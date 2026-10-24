from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import List, Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from . import jobs
from .beats import CATEGORIES, get_beat, load_beats, preview_path
from .cleanup import start_background_cleanup
from .config import get_settings
from .lyrics import FEELING_LABELS, MESSAGE_LABELS, SongRequestData
from .mixer import has_ffmpeg
from .safety import keyword_flag, resources, screen_text
from .vocals import VOICE_OPTIONS, get_provider

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("anthem")

AgeRange = Literal["13-17", "18-24", "25+"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop = start_background_cleanup()
    provider = get_provider()
    log.info("Vocal provider: %s | MP3 export: %s", provider.name, "yes" if has_ffmpeg() else "no (WAV fallback, install ffmpeg)")
    yield
    stop.set()


app = FastAPI(title="Anthem API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


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

@app.get("/health")
def health() -> dict:
    return {"ok": True, "vocal_provider": get_provider().name, "mp3": has_ffmpeg()}


@app.get("/beats")
def beats(category: Optional[str] = None) -> dict:
    items = [b.public() for b in load_beats() if not category or b.category == category]
    return {"categories": CATEGORIES, "beats": items}


@app.get("/beats/{beat_id}/preview")
def beat_preview(beat_id: str):
    beat = get_beat(beat_id)
    if not beat or not beat.path.exists():
        raise HTTPException(404, "Beat not found")
    path = preview_path(beat)
    return FileResponse(path, media_type="audio/mpeg" if path.suffix == ".mp3" else "audio/wav")


@app.get("/voices")
def voices() -> dict:
    return {"provider": get_provider().name, "voices": VOICE_OPTIONS}


@app.get("/support")
def support() -> dict:
    return {"resources": resources()}


@app.post("/screen")
def screen(body: ScreenIn) -> dict:
    result = screen_text(body.text, body.age_range)
    return {
        "flagged": result.flagged,
        "category": result.category,
        "method": result.method,
        "resources": resources() if result.flagged else [],
    }


@app.post("/songs", status_code=202)
def create_song(body: SongIn) -> dict:
    beat = get_beat(body.beat_id)
    if not beat:
        raise HTTPException(404, "Beat not found")
    if body.voice_id not in {v["id"] for v in VOICE_OPTIONS}:
        raise HTTPException(422, "Unknown voice")

    free_text = (body.free_text or "").strip() or None
    # The frontend omits free text after a crisis screen; this is a backstop so the
    # song never gets built around it.
    if free_text and keyword_flag(free_text):
        free_text = None

    req = SongRequestData(
        name=body.name,
        age_range=body.age_range,
        hobbies=body.hobbies,
        feelings=body.feelings,
        feelings_other=_clean(body.feelings_other) if body.feelings_other else None,
        messages=body.messages,
        custom_message=_clean(body.custom_message) if body.custom_message else None,
        beat=beat,
        free_text=free_text,
    )
    job = jobs.submit_song(req, body.voice_id)
    return {"job_id": job["id"]}


@app.get("/songs/{job_id}")
def song_status(job_id: str) -> dict:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "This song has expired or doesn't exist")
    return jobs.public_view(job)


@app.get("/songs/{job_id}/audio")
def song_audio(job_id: str, download: bool = Query(False)):
    job = jobs.get(job_id)
    if not job or job.get("status") != "done":
        raise HTTPException(404, "This song has expired or doesn't exist")
    path = jobs.job_dir(job_id) / job["audio_file"]
    if not path.exists():
        raise HTTPException(404, "This song has expired")
    ext = path.suffix.lstrip(".")
    title = "".join(c for c in (job.get("title") or "anthem") if c.isalnum() or c in " -_").strip() or "anthem"
    return FileResponse(
        path,
        media_type="audio/mpeg" if ext == "mp3" else "audio/wav",
        filename=f"{title}.{ext}" if download else None,
        content_disposition_type="attachment" if download else "inline",
        headers={"Cache-Control": "private, no-store"},
    )


@app.post("/songs/{job_id}/remix", status_code=202)
def remix(job_id: str, body: RemixIn) -> dict:
    source = jobs.get(job_id)
    if not source or source.get("status") != "done":
        raise HTTPException(404, "This song has expired or doesn't exist")
    if not (jobs.job_dir(job_id) / "vocals").exists():
        raise HTTPException(410, "This song's vocals have expired")
    beat = get_beat(body.beat_id)
    if not beat:
        raise HTTPException(404, "Beat not found")
    job = jobs.submit_remix(source, beat)
    return {"job_id": job["id"]}
