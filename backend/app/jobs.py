"""In-process job queue for song generation.

Jobs run on a small thread pool so HTTP requests return immediately and the
frontend polls for progress. Job state is mirrored to storage/jobs/<id>/job.json
(without any of the user's sensitive answers) so it survives a dev-server reload.
To move to Redis/RQ later, replace `submit()` and `get()`; the pipeline
functions don't depend on the queue.
"""
from __future__ import annotations

import json
import logging
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .beats import Beat, get_beat
from .claude import ClaudeUnavailable
from .config import get_settings
from .lyrics import SongRequestData, write_lyrics
from .mixer import VocalLine, mix_song
from .vocals import Delivery, VocalError, get_provider

log = logging.getLogger(__name__)

_lock = threading.Lock()
_jobs: Dict[str, dict] = {}
_executor: Optional[ThreadPoolExecutor] = None

STAGES = {
    "queued": "Getting ready",
    "writing": "Writing your lyrics",
    "singing": "Recording the vocals",
    "mixing": "Mixing your song",
    "done": "Your song is ready",
    "error": "Something went wrong",
}


def _pool() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=get_settings().max_workers, thread_name_prefix="song")
    return _executor


def job_dir(job_id: str) -> Path:
    return get_settings().jobs_dir / job_id


def _save(job: dict) -> None:
    d = job_dir(job["id"])
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "job.json.tmp"
    tmp.write_text(json.dumps(job))
    tmp.replace(d / "job.json")


def _update(job_id: str, **fields) -> dict:
    with _lock:
        job = _jobs[job_id]
        job.update(fields)
        job["updated_at"] = time.time()
        _save(job)
        return dict(job)


def get(job_id: str) -> Optional[dict]:
    # Ids are uuid4 hex; reject anything else before touching the filesystem.
    if len(job_id) != 32 or not all(c in "0123456789abcdef" for c in job_id):
        return None
    with _lock:
        if job_id in _jobs:
            return dict(_jobs[job_id])
    path = job_dir(job_id) / "job.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def forget(job_id: str) -> None:
    with _lock:
        _jobs.pop(job_id, None)


def _new_job(beat: Beat, voice_id: str, **extra) -> dict:
    job = {
        "id": uuid.uuid4().hex,
        "status": "queued",
        "stage": STAGES["queued"],
        "progress": 0.0,
        "created_at": time.time(),
        "updated_at": time.time(),
        "beat_id": beat.id,
        "voice_id": voice_id,
        "error": None,
        **extra,
    }
    with _lock:
        _jobs[job["id"]] = job
        _save(job)
    return job


def _run(job_id: str, fn: Callable[[], None]) -> None:
    try:
        fn()
    except (ClaudeUnavailable, VocalError) as e:
        log.warning("job %s failed: %s", job_id, type(e).__name__)
        _update(job_id, status="error", stage=STAGES["error"], error=_friendly(e))
    except Exception as e:  # noqa: BLE001 - surface any failure to the user, not a stuck spinner
        log.error("job %s crashed: %s", job_id, type(e).__name__)
        _update(job_id, status="error", stage=STAGES["error"], error="We couldn't finish your song. Please try again.")


def _friendly(e: Exception) -> str:
    if isinstance(e, ClaudeUnavailable):
        return "We couldn't write your lyrics just now. Please try again in a moment."
    return "We couldn't record the vocals just now. Please try again in a moment."


# ------------------------------------------------------------------ pipeline

def _record_vocals(job_id: str, sections: List[dict], beat: Beat, voice_id: str) -> List[VocalLine]:
    provider = get_provider()
    clips_dir = job_dir(job_id) / "vocals"
    clips_dir.mkdir(parents=True, exist_ok=True)

    flat = [(si, s["type"], text) for si, s in enumerate(sections) for text in s["lines"]]
    # Repeated choruses reuse the same recording.
    first_index: Dict[tuple, int] = {}
    for i, (_, st, t) in enumerate(flat):
        first_index.setdefault((st, t), i)
    unique: Dict[tuple, Path] = {}
    total = len(first_index)
    for n, ((stype, text), idx) in enumerate(first_index.items()):
        prev_text = flat[idx - 1][2] if idx > 0 else None
        next_text = flat[idx + 1][2] if idx + 1 < len(flat) else None
        seg = provider.synthesize(
            text, voice_id, Delivery(beat.category, beat.feel_bpm, stype), previous_text=prev_text, next_text=next_text
        )
        path = clips_dir / f"{n:02d}.wav"
        seg.export(path, format="wav")
        unique[(stype, text)] = path
        _update(job_id, progress=round(0.3 + 0.55 * (n + 1) / total, 3))

    return [VocalLine(section=si, section_type=st, text=t, clip=unique[(st, t)]) for si, st, t in flat]


def _mix(job_id: str, beat: Beat, lines: List[VocalLine], bars_per_line: int) -> None:
    _update(job_id, status="mixing", stage=STAGES["mixing"], progress=0.88)
    audio_path, timeline, duration_ms = mix_song(beat, lines, bars_per_line, job_dir(job_id) / "song")
    _update(
        job_id,
        status="done",
        stage=STAGES["done"],
        progress=1.0,
        audio_file=audio_path.name,
        timeline=timeline,
        duration=round(duration_ms / 1000, 2),
        clips=[{"section": l.section, "type": l.section_type, "text": l.text, "clip": l.clip.name} for l in lines],
    )


def submit_song(req: SongRequestData, voice_id: str) -> dict:
    # Only non-sensitive fields go into the persisted job record.
    job = _new_job(req.beat, voice_id, name=req.name)

    def work() -> None:
        _update(job["id"], status="writing", stage=STAGES["writing"], progress=0.08)
        lyrics = write_lyrics(req)
        req.free_text = None  # drop it as soon as the lyrics exist
        _update(
            job["id"],
            status="singing",
            stage=STAGES["singing"],
            progress=0.3,
            title=lyrics["title"],
            sections=lyrics["sections"],
            bars_per_line=lyrics["timing"]["bars_per_line"],
        )
        lines = _record_vocals(job["id"], lyrics["sections"], req.beat, voice_id)
        _mix(job["id"], req.beat, lines, lyrics["timing"]["bars_per_line"])

    _pool().submit(_run, job["id"], work)
    return job


def submit_remix(source: dict, beat: Beat) -> dict:
    """Same lyrics and recorded vocals, new beat: no new Claude or TTS calls."""
    src_dir = job_dir(source["id"]) / "vocals"
    job = _new_job(
        beat,
        source["voice_id"],
        name=source.get("name"),
        title=source.get("title"),
        sections=source.get("sections"),
        bars_per_line=source.get("bars_per_line"),
        remix_of=source["id"],
    )

    def work() -> None:
        dst = job_dir(job["id"]) / "vocals"
        shutil.copytree(src_dir, dst)
        lines = [
            VocalLine(section=c["section"], section_type=c["type"], text=c["text"], clip=dst / c["clip"])
            for c in source["clips"]
        ]
        # Keep each line roughly the same length in seconds on the new tempo.
        old = get_beat(source["beat_id"])
        bars = source.get("bars_per_line") or 1
        if old:
            seconds = bars * 60.0 / old.bpm * old.beats_per_bar
            bars = max(1, round(seconds / (60.0 / beat.bpm * beat.beats_per_bar)))
        _mix(job["id"], beat, lines, bars)

    _pool().submit(_run, job["id"], work)
    return job


def public_view(job: dict) -> dict:
    view = {k: job.get(k) for k in ("id", "status", "stage", "progress", "error", "beat_id", "voice_id", "title")}
    if job.get("status") == "done":
        view.update(
            sections=job.get("sections"),
            timeline=job.get("timeline"),
            duration=job.get("duration"),
            audio_url=f"/songs/{job['id']}/audio",
            audio_format=Path(job["audio_file"]).suffix.lstrip("."),
            expires_at=job["created_at"] + get_settings().retention_hours * 3600,
        )
    return view
