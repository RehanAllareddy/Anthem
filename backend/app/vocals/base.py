from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

from pydub import AudioSegment

# Generic voice options shown in the UI. Each provider maps these ids to real voices.
VOICE_OPTIONS = [
    {"id": "warm", "label": "Warm", "description": "Friendly and reassuring"},
    {"id": "bright", "label": "Bright", "description": "Light and upbeat"},
    {"id": "deep", "label": "Deep", "description": "Grounded and steady"},
]


@dataclass(frozen=True)
class Delivery:
    category: str  # beat category: rap | pop | chill | rock | upbeat
    bpm: float
    section: str  # verse | chorus


class VocalError(RuntimeError):
    def __init__(self, message: str, code: str = "vocals_failed", detail: str = ""):
        super().__init__(message)
        # Short, non-sensitive reason and provider message, shown to the client for troubleshooting.
        self.code = code
        self.detail = detail


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
    ) -> AudioSegment:
        """Return one line of vocals (any sample rate; the mixer normalizes)."""
