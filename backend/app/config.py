from __future__ import annotations

import os
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
ON_VERCEL = os.environ.get("VERCEL_ENV") in ("production", "preview")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Claude (lyrics + safety screening)
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-opus-5-5"
    # Lyrics + wellbeing screening: "claude", "template" (fixed per-genre lyrics,
    # keyword-only screening), or "auto" (Claude when ANTHROPIC_API_KEY is set).
    lyrics_provider: str = "auto"

    # Vocals: "elevenlabs", "local", or "auto" (ElevenLabs when a key is set, else local)
    vocal_provider: str = "auto"
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_model_id: str = "eleven_multilingual_v2"
    # Override the preset voices with your own ElevenLabs voice IDs if you like.
    elevenlabs_voice_warm: str = "21m00Tcm4TlvDq8ikWAM"
    elevenlabs_voice_bright: str = "EXAVITQu4vr4xnygBOkJ"
    elevenlabs_voice_deep: str = "pNInz6obpgDQGcFmaJgB"
    elevenlabs_voice_smooth: str = "ErXwobaYiR6NdRHJ7Mlw"

    # Where songs and job state live: "blob" (Vercel Blob), "local" (disk), or
    # "auto" (Blob when a Blob store is connected, else disk).
    storage_backend: str = "auto"
    # How generation runs: "vercel" (Vercel Queues), "local" (in-process threads),
    # or "auto" (Queues on Vercel preview/production, threads everywhere else).
    task_backend: str = "auto"

    beats_dir: Path = BACKEND_ROOT / "beats"
    # Vercel functions can only write to /tmp.
    storage_dir: Path = (Path(tempfile.gettempdir()) / "anthem") if os.environ.get("VERCEL") else REPO_ROOT / "storage"

    # Privacy
    retention_hours: float = 24.0
    cleanup_interval_minutes: float = 30.0

    # Server
    api_prefix: str = "/api"
    max_workers: int = 2

    @property
    def use_blob(self) -> bool:
        if self.storage_backend == "auto":
            return bool(os.environ.get("BLOB_STORE_ID") or os.environ.get("BLOB_READ_WRITE_TOKEN"))
        return self.storage_backend == "blob"

    @property
    def use_vercel_queues(self) -> bool:
        if self.task_backend == "auto":
            return ON_VERCEL
        return self.task_backend == "vercel"

    @property
    def use_claude(self) -> bool:
        if self.lyrics_provider == "auto":
            return bool(self.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY"))
        return self.lyrics_provider == "claude"

    def setup_problems(self) -> List[str]:
        """Configuration that will stop songs from being made. Safe to show: no secrets."""
        problems = []
        if self.use_vercel_queues and not self.use_blob:
            problems.append(
                "No Vercel Blob store is connected. The queue worker runs on a different instance "
                "and can't see jobs saved to local disk. Create a Private Blob store and connect it to this project."
            )
        if self.lyrics_provider == "claude" and not (self.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")):
            problems.append("LYRICS_PROVIDER=claude but ANTHROPIC_API_KEY is not set.")
        if ON_VERCEL and not self.elevenlabs_api_key and self.vocal_provider != "local":
            problems.append("ELEVENLABS_API_KEY is not set. Vercel has no built-in text-to-speech, so vocals can't be recorded.")
        return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()
