"""Song jobs: state, the generation pipeline, and expiry.

The API creates a job and enqueues a message (tasks.enqueue); a worker (a Vercel
Queues subscriber in production, a local thread in development) runs it. Several
instances may serve one user, so storage is the single source of truth:

    jobs/<id>/state/<ms>-<seq>.json   immutable state snapshots, newest wins
    jobs/<id>/vocals/NN.wav           one recorded clip per unique lyric line
    jobs/<id>/song.<mp3|wav>          the finished mix

Nothing the user typed about how they feel is ever written to storage.
"""
from __future__ import annotations

import io
import json
import logging
import re
import secrets
import time
from typing import Dict, List, Optional

from pydub import AudioSegment

from . import tasks
from .beats import Beat, get_beat
from .claude import ClaudeUnavailable
from .config import get_settings
from .lyrics import SongRequestData, write_lyrics
from .mixer import VocalLine, decode_wav, mix_song
from .storage import get_storage
from .vocals import Delivery, VocalError, get_provider

log = logging.getLogger(__name__)

STAGES = {
    "queued": "Getting ready",
    "writing": "Writing your lyrics",
    "singing": "Recording the vocals",
    "mixing": "Mixing your song",
    "done": "Your song is ready",
    "error": "Something went wrong",
}
FINAL = ("done", "error")
_ID_RE = re.compile(r"^[0-9a-f]{32}$")
PROGRESS_WRITE_INTERVAL_S = 3.0


# ------------------------------------------------------------------- ids

def new_job_id(now: Optional[float] = None) -> str:
    """32 hex chars: 8 for the creation time (so cleanup needs no reads) + 24 random."""
    return f"{int(now or time.time()):08x}{secrets.token_hex(12)}"


def created_at(job_id: str) -> float:
    return float(int(job_id[:8], 16))


def valid_id(job_id: str) -> bool:
    return bool(_ID_RE.match(job_id))


def _prefix(job_id: str) -> str:
    return f"jobs/{job_id}/"


# ----------------------------------------------------------------- state

def get(job_id: str) -> Optional[dict]:
    if not valid_id(job_id):
        return None
    store = get_storage()
    snapshots = store.list(_prefix(job_id) + "state/")
    if not snapshots:
        return None
    data = store.get(snapshots[-1])
    return json.loads(data) if data else None


class JobRecorder:
    """Writes state snapshots for a job. Only one worker writes a given job."""

    def __init__(self, state: dict):
        self.state = state
        self._seq = 0
        self._last_write = 0.0

    def update(self, **fields) -> None:
        status_changed = "status" in fields and fields["status"] != self.state.get("status")
        self.state.update(fields)
        self.state["updated_at"] = time.time()
        # Progress ticks are throttled; status changes are always written.
        if status_changed or time.time() - self._last_write >= PROGRESS_WRITE_INTERVAL_S:
            self.flush()

    def flush(self) -> None:
        self._seq += 1
        path = f"{_prefix(self.state['id'])}state/{int(time.time() * 1000):013d}-{self._seq:04d}.json"
        get_storage().put(path, json.dumps(self.state).encode(), "application/json")
        self._last_write = time.time()


def _initial_state(job_id: str, beat: Beat, voice_id: str, **extra) -> dict:
    return {
        "id": job_id,
        "status": "queued",
        "stage": STAGES["queued"],
        "progress": 0.0,
        "created_at": created_at(job_id),
        "updated_at": time.time(),
        "beat_id": beat.id,
        "voice_id": voice_id,
        "error": None,
        **extra,
    }


def _friendly(e: Exception) -> str:
    if isinstance(e, ClaudeUnavailable):
        return "We couldn't write your lyrics just now. Please try again in a moment."
    if isinstance(e, VocalError):
        return "We couldn't record the vocals just now. Please try again in a moment."
    return "We couldn't finish your song. Please try again."


# --------------------------------------------------------------- creating

def _schedule_expiry(job_id: str) -> None:
    delay = get_settings().retention_hours * 3600
    if delay >= tasks.MAX_RETENTION_S:
        return  # longer than a queue message can wait; the sweep handles it
    tasks.enqueue(
        {"kind": "expire", "job_id": job_id},
        delay_s=delay,
        retention_s=min(delay + 3600, tasks.MAX_RETENTION_S),
    )


def create_song(request: dict, beat: Beat, voice_id: str, name: str) -> str:
    """request: validated SongIn fields. May include free_text, which only travels
    inside the short-lived queue message."""
    job_id = new_job_id()
    JobRecorder(_initial_state(job_id, beat, voice_id, name=name)).flush()
    tasks.enqueue(
        {"kind": "song", "job_id": job_id, "request": request},
        retention_s=tasks.SONG_MESSAGE_RETENTION_S,
    )
    _schedule_expiry(job_id)
    return job_id


def create_remix(source: dict, beat: Beat) -> str:
    job_id = new_job_id()
    JobRecorder(
        _initial_state(
            job_id,
            beat,
            source["voice_id"],
            name=source.get("name"),
            title=source.get("title"),
            sections=source.get("sections"),
            remix_of=source["id"],
        )
    ).flush()
    tasks.enqueue({"kind": "remix", "job_id": job_id, "source_id": source["id"]})
    _schedule_expiry(job_id)
    return job_id


# ---------------------------------------------------------------- worker

def handle_message(message: dict) -> None:
    """Entry point for a queued message. Safe to call more than once per message."""
    kind, job_id = message.get("kind"), message.get("job_id", "")
    if not valid_id(job_id):
        log.warning("dropping message with invalid job id")
        return
    if kind == "expire":
        delete_job(job_id)
        return

    state = get(job_id)
    if state is None:
        # Usually means the API and this worker don't share storage (no Blob store connected).
        log.error("job %s: no saved state found; is a Blob store connected?", job_id)
        return
    if state.get("status") in FINAL:
        return  # a redelivery of a job that already finished
    rec = JobRecorder(state)
    try:
        if kind == "song":
            _run_song(rec, message["request"])
        elif kind == "remix":
            _run_remix(rec, message["source_id"])
        else:
            log.warning("unknown message kind %r", kind)
    except Exception as e:  # noqa: BLE001 - always end in a state the user can see
        log.warning("job %s failed: %s", job_id, type(e).__name__)
        rec.update(status="error", stage=STAGES["error"], error=_friendly(e))


def _run_song(rec: JobRecorder, request: dict) -> None:
    beat = get_beat(request["beat_id"])
    if beat is None:
        raise ValueError("beat no longer exists")
    req = SongRequestData(
        name=request["name"],
        age_range=request["age_range"],
        hobbies=request["hobbies"],
        feelings=request["feelings"],
        feelings_other=request.get("feelings_other"),
        messages=request.get("messages", []),
        custom_message=request.get("custom_message"),
        beat=beat,
        free_text=request.get("free_text"),
    )
    rec.update(status="writing", stage=STAGES["writing"], progress=0.08)
    lyrics = write_lyrics(req)
    req.free_text = None  # drop it as soon as the lyrics exist
    request.pop("free_text", None)
    rec.update(
        status="singing",
        stage=STAGES["singing"],
        progress=0.3,
        title=lyrics["title"],
        sections=lyrics["sections"],
        bars_per_line=lyrics["timing"]["bars_per_line"],
    )
    lines = _record_vocals(rec, lyrics["sections"], beat, rec.state["voice_id"])
    _mix(rec, beat, lines, lyrics["timing"]["bars_per_line"])


def _record_vocals(rec: JobRecorder, sections: List[dict], beat: Beat, voice_id: str) -> List[VocalLine]:
    provider = get_provider()
    store = get_storage()
    flat = [(si, s["type"], text) for si, s in enumerate(sections) for text in s["lines"]]
    # Repeated choruses reuse the same recording.
    first_index: Dict[tuple, int] = {}
    for i, (_, st, t) in enumerate(flat):
        first_index.setdefault((st, t), i)

    clips: Dict[tuple, str] = {}
    total = len(first_index)
    for n, ((stype, text), idx) in enumerate(first_index.items()):
        prev_text = flat[idx - 1][2] if idx > 0 else None
        next_text = flat[idx + 1][2] if idx + 1 < len(flat) else None
        seg = provider.synthesize(
            text, voice_id, Delivery(beat.category, beat.feel_bpm, stype), previous_text=prev_text, next_text=next_text
        )
        buf = io.BytesIO()
        seg.export(buf, format="wav")
        path = f"{_prefix(rec.state['id'])}vocals/{n:02d}.wav"
        store.put(path, buf.getvalue(), "audio/wav")
        clips[(stype, text)] = path
        rec.update(progress=round(0.3 + 0.55 * (n + 1) / total, 3))

    return [VocalLine(section=si, section_type=st, text=t, clip=clips[(st, t)]) for si, st, t in flat]


def _load_clip(path: str) -> AudioSegment:
    data = get_storage().get(path)
    if data is None:
        raise FileNotFoundError("vocal clip has expired")
    return decode_wav(data)


def _mix(rec: JobRecorder, beat: Beat, lines: List[VocalLine], bars_per_line: int) -> None:
    rec.update(status="mixing", stage=STAGES["mixing"], progress=0.88)
    audio, ext, timeline, duration_ms = mix_song(beat, lines, bars_per_line, _load_clip)
    audio_path = f"{_prefix(rec.state['id'])}song.{ext}"
    get_storage().put(audio_path, audio, "audio/mpeg" if ext == "mp3" else "audio/wav")
    rec.update(
        status="done",
        stage=STAGES["done"],
        progress=1.0,
        audio_path=audio_path,
        timeline=timeline,
        duration=round(duration_ms / 1000, 2),
        bars_per_line=bars_per_line,
        clips=[{"section": l.section, "type": l.section_type, "text": l.text, "clip": l.clip} for l in lines],
    )


def _run_remix(rec: JobRecorder, source_id: str) -> None:
    """Same lyrics and recorded vocals, new beat: no new Claude or TTS calls."""
    source = get(source_id)
    beat = get_beat(rec.state["beat_id"])
    if not source or source.get("status") != "done" or beat is None:
        raise FileNotFoundError("source song has expired")
    lines = [
        VocalLine(section=c["section"], section_type=c["type"], text=c["text"], clip=c["clip"]) for c in source["clips"]
    ]
    # Keep each line roughly the same length in seconds on the new tempo.
    old = get_beat(source["beat_id"])
    bars = source.get("bars_per_line") or 1
    if old:
        seconds = bars * 60.0 / old.bpm * old.beats_per_bar
        bars = max(1, round(seconds / (60.0 / beat.bpm * beat.beats_per_bar)))
    _mix(rec, beat, lines, bars)


# ----------------------------------------------------------------- expiry

def delete_job(job_id: str) -> None:
    get_storage().delete_prefix(_prefix(job_id))


def purge_expired(now: Optional[float] = None) -> int:
    """Delete every job older than the retention window. Returns how many."""
    cutoff = (now or time.time()) - get_settings().retention_hours * 3600
    removed = 0
    for job_id in get_storage().folders("jobs/"):
        if valid_id(job_id) and created_at(job_id) < cutoff:
            delete_job(job_id)
            removed += 1
    if removed:
        log.info("cleanup: removed %d expired song(s)", removed)
    return removed


# ---------------------------------------------------------------- views

def audio(job: dict) -> Optional[bytes]:
    path = job.get("audio_path")
    return get_storage().get(path) if path else None


def public_view(job: dict) -> dict:
    view = {k: job.get(k) for k in ("id", "status", "stage", "progress", "error", "beat_id", "voice_id", "title")}
    if job.get("status") == "done":
        view.update(
            sections=job.get("sections"),
            timeline=job.get("timeline"),
            duration=job.get("duration"),
            audio_url=f"/songs/{job['id']}/audio",
            audio_format=job["audio_path"].rsplit(".", 1)[-1],
            expires_at=job["created_at"] + get_settings().retention_hours * 3600,
        )
    return view
