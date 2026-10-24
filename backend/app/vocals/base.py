from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from pydub import AudioSegment

# Generic voice options shown in the UI. Each provider maps these ids to real voices.
VOICE_OPTIONS = [
    {"id": "warm", "label": "Warm", "description": "Friendly and reassuring"},
    {"id": "bright", "label": "Bright", "description": "Light and upbeat"},
    {"id": "deep", "label": "Deep", "description": "Grounded and steady"},
    {"id": "smooth", "label": "Smooth", "description": "Relaxed and mellow"},
]


@dataclass(frozen=True)
class Delivery:
    category: str  # beat category: rap | pop | chill | rock | upbeat
    bpm: float
    section: str  # verse | chorus


class VocalError(RuntimeError):
    def __init__(self, message: str, code: str = "vocals_failed"):
        super().__init__(message)
        self.code = code  # short, non-sensitive reason shown to the client for troubleshooting


class VocalProvider(ABC):
    name: str

    def voices(self) -> List[dict]:
        return VOICE_OPTIONS

    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice_id: str,
        delivery: Delivery,
        previous_text: Optional[str] = None,
        next_text: Optional[str] = None,
    ) -> AudioSegment:
        """Return one line of vocals (any sample rate; the mixer normalizes)."""
