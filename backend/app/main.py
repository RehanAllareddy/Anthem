from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List, Literal, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator

from . import jobs, tasks
from .beats import CATEGORIES, get_beat, load_beats, preview_audio
from .cleanup import maybe_sweep, start_background_cleanup
from .config import get_settings
from .lyrics import FEELING_LABELS, MESSAGE_LABELS, has_profanity
from .mixer import has_ffmpeg
from .safety import keyword_flag, resources, screen_text
from .storage import get_storage
from .vocals import VOICE_OPTIONS, get_provider

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("anthem")

AgeRange = Literal["13-17", "18-24", "25+"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # On Vercel, expiry is driven by delayed queue messages; a background thread
    # wouldn't run reliably between requests.
    stop = start_background_cleanup() if settings.task_mode == "local" else None
    log.info(
        "Vocals: %s | storage: %s | tasks: %s | MP3 export: %s",
        get_provider().name,
        get_storage().name,
        settings.task_mode,
        "yes" if has_ffmpeg() else "no (WAV fallback)",
    )
    yield
    if stop:
        stop.set()


# This service is internal: the only caller is the Next.js frontend's /api proxy
# (over a Vercel service binding), so there's no CORS. Routes live under
# API_PREFIX ("/api"), matching the paths the proxy forwards. URLs returned to the
# client (preview_url, audio_url) are relative to this prefix.
app = FastAPI(title="Anthem API", lifespan=lifespan)
router = APIRouter()


# ------------------------------------------------------------------ schemas

def _clean(s: str) -> str:
    return " ".join(s.split())


class ScreenIn(BaseModel):
    text: str = Field(max_length=1000)
    age_range: AgeRange


class SongIn(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    age_range: AgeRange
    hobbies: List[str] = Field(min_length=2, max_length=5)
    feelings: List[str] = Field(min_length=1, max_length=7)
    feelings_other: Optional[str] = Field(default=None, max_length=60)
    free_text: Optional[str] = Field(default=None, max_length=1000)
    messages: List[str] = Field(default_factory=list, max_length=6)
    custom_message: Optional[str] = Field(default=None, max_length=80)
    beat_id: str
    voice_id: str = "warm"

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = _clean(v)
        if not v:
            raise ValueError("name is required")
        return v

    @field_validator("hobbies")
    @classmethod
    def _hobbies(cls, v: List[str]) -> List[str]:
        out = [_clean(h)[:40] for h in v if _clean(h)]
        if len(out) < 2:
            raise ValueError("add at least two hobbies")
        return out

    @field_validator("feelings")
    @classmethod
    def _feelings(cls, v: List[str]) -> List[str]:
        bad = [f for f in v if f not in FEELING_LABELS]
        if bad:
            raise ValueError(f"unknown feelings: {bad}")
        return v

    @field_validator("messages")
    @classmethod
    def _messages(cls, v: List[str]) -> List[str]:
        bad = [m for m in v if m not in MESSAGE_LABELS]
        if bad:
            raise ValueError(f"unknown messages: {bad}")
        return v


class RemixIn(BaseModel):
    beat_id: str


# ------------------------------------------------------------------- routes

@router.get("/health")
def health() -> dict:
    settings = get_settings()
    problems = settings.setup_problems()
    return {
        "ok": not problems,
        "problems": problems,
        "lyrics": "claude" if settings.use_claude else "template",
        "storage": get_storage().name,
        "tasks": settings.task_mode,
        "vocal_provider": get_provider().name,
        "mp3": has_ffmpeg(),
    }


@router.get("/beats")
def beats(category: Optional[str] = None) -> dict:
    items = [b.public() for b in load_beats() if not category or b.category == category]
    return {"categories": CATEGORIES, "beats": items}


@router.get("/beats/{beat_id}/preview")
def beat_preview(beat_id: str):
    beat = get_beat(beat_id)
    if not beat or not beat.path.exists():
        raise HTTPException(404, "Beat not found")
    data, ext = preview_audio(beat)
    return Response(
        data,
        media_type="audio/mpeg" if ext == "mp3" else "audio/wav",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/voices")
def voices() -> dict:
    return {"provider": get_provider().name, "voices": VOICE_OPTIONS}


@router.get("/support")
def support() -> dict:
    return {"resources": resources()}


@router.post("/screen")
def screen(body: ScreenIn) -> dict:
    result = screen_text(body.text, body.age_range)
    return {
        "flagged": result.flagged,
        "category": result.category,
        "method": result.method,
        "resources": resources() if result.flagged else [],
    }


@router.post("/songs", status_code=202)
async def create_song(body: SongIn) -> dict:
    beat = get_beat(body.beat_id)
    if not beat:
        raise HTTPException(404, "Beat not found")
    if body.voice_id not in {v["id"] for v in VOICE_OPTIONS}:
        raise HTTPException(422, "Unknown voice")

    problems = get_settings().setup_problems()
    if problems:
        log.error("refusing to start song: %s", " | ".join(problems))
        raise HTTPException(503, "Anthem isn't fully set up yet: " + " ".join(problems))

    # Names, hobbies and custom words go straight into the lyrics (always, with templates).
    typed = [body.name, *body.hobbies, body.custom_message or "", body.feelings_other or ""]
    if has_profanity(typed):
        raise HTTPException(422, "Let's keep your song kind and clean. Please choose different words.")

    free_text = (body.free_text or "").strip() or None
    # The frontend omits free text after a crisis screen; this is a backstop so the
    # song never gets built around it.
    if free_text and keyword_flag(free_text):
        free_text = None

    request = body.model_dump()
    request.update(
        feelings_other=_clean(body.feelings_other) if body.feelings_other else None,
        custom_message=_clean(body.custom_message) if body.custom_message else None,
        free_text=free_text,
    )
    try:
        # Storage calls block, so run them off the event loop; dispatch must run on
        # it, because wait_until ties the work to this request.
        job_id, message = await asyncio.to_thread(jobs.create_song, request, beat, body.voice_id, body.name)
        tasks.dispatch(message, retention_s=tasks.SONG_MESSAGE_RETENTION_S)
    except Exception as e:  # noqa: BLE001
        log.error("could not start song: %s", type(e).__name__)
        raise HTTPException(503, "We couldn't start your song just now. Please try again.") from None
    await asyncio.to_thread(maybe_sweep)
    return {"job_id": job_id}


@router.get("/songs/{job_id}")
def song_status(job_id: str) -> dict:
    maybe_sweep()  # cheap unless a sweep is due; keeps retention working without a scheduler
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "This song has expired or doesn't exist")
    return jobs.public_view(job)


@router.get("/songs/{job_id}/audio")
def song_audio(job_id: str, download: bool = Query(False)):
    job = jobs.get(job_id)
    if not job or job.get("status") != "done":
        raise HTTPException(404, "This song has expired or doesn't exist")
    data = jobs.audio(job)
    if data is None:
        raise HTTPException(404, "This song has expired")
    ext = job["audio_path"].rsplit(".", 1)[-1]
    title = "".join(c for c in (job.get("title") or "anthem") if c.isalnum() or c in " -_").strip() or "anthem"
    disposition = f'attachment; filename="{title}.{ext}"' if download else "inline"
    return Response(
        data,
        media_type="audio/mpeg" if ext == "mp3" else "audio/wav",
        headers={"Cache-Control": "private, no-store", "Content-Disposition": disposition},
    )


@router.post("/songs/{job_id}/remix", status_code=202)
async def remix(job_id: str, body: RemixIn) -> dict:
    source = await asyncio.to_thread(jobs.get, job_id)
    if not source or source.get("status") != "done":
        raise HTTPException(404, "This song has expired or doesn't exist")
    beat = get_beat(body.beat_id)
    if not beat:
        raise HTTPException(404, "Beat not found")
    try:
        new_id, message = await asyncio.to_thread(jobs.create_remix, source, beat)
        tasks.dispatch(message)
    except Exception as e:  # noqa: BLE001
        log.error("could not start remix: %s", type(e).__name__)
        raise HTTPException(503, "We couldn't start your remix just now. Please try again.") from None
    return {"job_id": new_id}


app.include_router(router, prefix=get_settings().api_prefix)
