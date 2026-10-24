from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT / ".env", ROOT / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Claude (lyrics + safety screening)
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-opus-5-5"

    # Vocals: "elevenlabs", "local", or "auto" (ElevenLabs when a key is set, else local)
    vocal_provider: str = "auto"
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_model_id: str = "eleven_multilingual_v2"
    # Override the preset voices with your own ElevenLabs voice IDs if you like.
    elevenlabs_voice_warm: str = "21m00Tcm4TlvDq8ikWAM"
    elevenlabs_voice_bright: str = "EXAVITQu4vr4xnygBOkJ"
    elevenlabs_voice_deep: str = "pNInz6obpgDQGcFmaJgB"
    elevenlabs_voice_smooth: str = "ErXwobaYiR6NdRHJ7Mlw"

    # Storage & privacy
    beats_dir: Path = ROOT / "beats"
    storage_dir: Path = ROOT / "storage"
    retention_hours: float = 24.0
    cleanup_interval_minutes: float = 30.0

    # Server
    cors_origins: List[str] = ["http://localhost:3000"]
    max_workers: int = 2

    @property
    def jobs_dir(self) -> Path:
        return self.storage_dir / "jobs"

    @property
    def previews_dir(self) -> Path:
        return self.storage_dir / "previews"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.jobs_dir.mkdir(parents=True, exist_ok=True)
    s.previews_dir.mkdir(parents=True, exist_ok=True)
    return s
