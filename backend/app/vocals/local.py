"""Offline vocals for development: macOS `say` or espeak-ng. Robotic, but free."""
from __future__ import annotations

import platform
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from pydub import AudioSegment

from .base import Delivery, VocalError, VocalProvider

# Words per minute per genre.
_RATE = {"rap": 210, "upbeat": 190, "rock": 185, "pop": 175, "chill": 150}

# Preferred macOS voices per option, first installed one wins.
_SAY_VOICES: Dict[str, List[str]] = {
    "warm": ["Samantha", "Karen", "Moira"],
    "bright": ["Tessa", "Karen", "Samantha"],
    "deep": ["Daniel", "Alex", "Fred"],
}
_ESPEAK_VOICES = {"warm": "en-us+f3", "bright": "en-us+f4", "deep": "en-us+m3"}


@lru_cache
def _installed_say_voices() -> set:
    out = subprocess.run(["say", "-v", "?"], capture_output=True, text=True).stdout
    return {line.split()[0] for line in out.splitlines() if line.strip()}


class LocalProvider(VocalProvider):
    name = "local"

    def __init__(self) -> None:
        if platform.system() == "Darwin" and shutil.which("say"):
            self._engine = "say"
        elif shutil.which("espeak-ng"):
            self._engine = "espeak-ng"
        else:
            self._engine = None

    def synthesize(
        self,
        text: str,
        voice_id: str,
        delivery: Delivery,
    ) -> AudioSegment:
        rate = _RATE.get(delivery.category, 175)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "line.wav"
            if self._engine == "say":
                cmd = ["say", "-r", str(rate), "-o", str(out), "--data-format=LEI16@22050"]
                voice = next((v for v in _SAY_VOICES.get(voice_id, []) if v in _installed_say_voices()), None)
                if voice:
                    cmd += ["-v", voice]
                cmd.append(text)
            elif self._engine == "espeak-ng":
                cmd = ["espeak-ng", "-s", str(rate), "-v", _ESPEAK_VOICES.get(voice_id, "en-us"), "-w", str(out), text]
            else:
                raise VocalError("No local TTS engine found (install espeak-ng, or set ELEVENLABS_API_KEY)")
            proc = subprocess.run(cmd, capture_output=True)
            if proc.returncode != 0 or not out.exists():
                raise VocalError(f"Local TTS failed ({self._engine})")
            return AudioSegment.from_wav(out)
