from __future__ import annotations

import time
from typing import Dict, Optional

import httpx
from pydub import AudioSegment

from .base import Delivery, VocalError, VocalProvider

API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
SAMPLE_RATE = 24000  # raw PCM output avoids needing ffmpeg to decode

# Expressiveness per genre: lower stability = more animated delivery.
_SETTINGS: Dict[str, dict] = {
    "rap": {"stability": 0.3, "similarity_boost": 0.8, "style": 0.55, "speed": 1.1},
    "upbeat": {"stability": 0.35, "similarity_boost": 0.8, "style": 0.5, "speed": 1.05},
    "rock": {"stability": 0.35, "similarity_boost": 0.8, "style": 0.5, "speed": 1.05},
    "pop": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.4, "speed": 1.0},
    "chill": {"stability": 0.6, "similarity_boost": 0.75, "style": 0.25, "speed": 0.9},
}


def _error_code(resp: httpx.Response) -> str:
    """e.g. "elevenlabs_401_missing_permissions", from ElevenLabs' {"detail": {"status": ...}}."""
    reason = ""
    try:
        detail = resp.json().get("detail")
        if isinstance(detail, dict):
            reason = str(detail.get("status") or detail.get("code") or "")
    except ValueError:
        pass
    reason = "".join(c if c.isalnum() else "_" for c in reason)[:60]
    return f"elevenlabs_{resp.status_code}" + (f"_{reason}" if reason else "")


class ElevenLabsProvider(VocalProvider):
    name = "elevenlabs"

    def __init__(self, api_key: str, model_id: str, voice_map: Dict[str, str]):
        self._model_id = model_id
        self._voice_map = voice_map
        self._http = httpx.Client(headers={"xi-api-key": api_key}, timeout=60.0)

    def synthesize(
        self,
        text: str,
        voice_id: str,
        delivery: Delivery,
        previous_text: Optional[str] = None,
        next_text: Optional[str] = None,
    ) -> AudioSegment:
        voice = self._voice_map.get(voice_id) or next(iter(self._voice_map.values()))
        settings = dict(_SETTINGS.get(delivery.category, _SETTINGS["pop"]))
        speed = settings.pop("speed")
        body = {
            "text": text,
            "model_id": self._model_id,
            "voice_settings": {**settings, "use_speaker_boost": True, "speed": speed},
        }
        # Neighbouring lines help the model keep a consistent, flowing delivery.
        if previous_text:
            body["previous_text"] = previous_text
        if next_text:
            body["next_text"] = next_text

        url = API_URL.format(voice_id=voice)
        for attempt in range(4):
            resp = self._http.post(url, params={"output_format": f"pcm_{SAMPLE_RATE}"}, json=body)
            if resp.status_code == 200:
                return AudioSegment(data=resp.content, sample_width=2, frame_rate=SAMPLE_RATE, channels=1)
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(float(resp.headers.get("retry-after", 2 ** attempt)))
                continue
            # Don't include the request body (lyrics) in errors.
            raise VocalError(f"ElevenLabs returned HTTP {resp.status_code}", code=_error_code(resp))
        raise VocalError("ElevenLabs retries exhausted")
