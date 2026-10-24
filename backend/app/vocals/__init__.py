from __future__ import annotations

from functools import lru_cache

from ..config import get_settings
from .base import VOICE_OPTIONS, Delivery, VocalError, VocalProvider

__all__ = ["get_provider", "Delivery", "VocalError", "VocalProvider", "VOICE_OPTIONS"]


@lru_cache
def get_provider() -> VocalProvider:
    """Pick the vocal provider from VOCAL_PROVIDER (elevenlabs | local | auto)."""
    s = get_settings()
    choice = s.vocal_provider.lower()
    if choice == "auto":
        choice = "elevenlabs" if s.elevenlabs_api_key else "local"

    if choice == "elevenlabs":
        if not s.elevenlabs_api_key:
            raise RuntimeError("VOCAL_PROVIDER=elevenlabs but ELEVENLABS_API_KEY is not set")
        from .elevenlabs import ElevenLabsProvider

        return ElevenLabsProvider(
            api_key=s.elevenlabs_api_key,
            model_id=s.elevenlabs_model_id,
            voice_map={
                "warm": s.elevenlabs_voice_warm,
                "bright": s.elevenlabs_voice_bright,
                "deep": s.elevenlabs_voice_deep,
                "smooth": s.elevenlabs_voice_smooth,
            },
        )
    if choice == "local":
        from .local import LocalProvider

        return LocalProvider()
    raise RuntimeError(f"Unknown VOCAL_PROVIDER {s.vocal_provider!r}")
