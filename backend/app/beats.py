"""Beat library: reads beats/beats.json and serves loop files and previews."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel
from pydub import AudioSegment

from .config import get_settings

CATEGORIES = ["upbeat", "chill", "pop", "rap", "rock"]
PREVIEW_MS = 10_000


class Beat(BaseModel):
    id: str
    name: str
    category: str
    bpm: float
    key: str
    mood: str
    file: str
    license: str
    source_url: str
    bars: int = 8
    beats_per_bar: int = 4
    feel: Optional[str] = None  # "halftime" for trap-style beats

    @property
    def path(self) -> Path:
        return get_settings().beats_dir / self.file

    @property
    def feel_bpm(self) -> float:
        """Tempo the vocal delivery should follow."""
        return self.bpm / 2 if self.feel == "halftime" else self.bpm

    def public(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "bpm": self.bpm,
            "key": self.key,
            "mood": self.mood,
            "license": self.license,
            "source_url": self.source_url,
            "preview_url": f"/beats/{self.id}/preview",
        }


_cache: Dict[str, object] = {}


def load_beats() -> List[Beat]:
    manifest = get_settings().beats_dir / "beats.json"
    mtime = manifest.stat().st_mtime
    if _cache.get("mtime") != mtime:
        raw = json.loads(manifest.read_text())["beats"]
        _cache["beats"] = [Beat(**b) for b in raw]
        _cache["mtime"] = mtime
    return _cache["beats"]  # type: ignore[return-value]


def get_beat(beat_id: str) -> Optional[Beat]:
    return next((b for b in load_beats() if b.id == beat_id), None)


def load_loop(beat: Beat) -> AudioSegment:
    loop = AudioSegment.from_file(beat.path)
    return loop.set_frame_rate(44100).set_channels(2).set_sample_width(2)


_previews: Dict[str, Tuple[bytes, str]] = {}


def preview_audio(beat: Beat) -> Tuple[bytes, str]:
    """10-second preview as (bytes, extension), rendered once per instance."""
    key = f"{beat.id}:{beat.path.stat().st_mtime}"
    if key not in _previews:
        from .mixer import encode  # local import avoids a cycle

        loop = load_loop(beat)
        clip = (loop * math.ceil(PREVIEW_MS / len(loop)))[:PREVIEW_MS].fade_in(150).fade_out(1200)
        _previews[key] = encode(clip)
    return _previews[key]
