# Anthem

Anthem helps teens and adults cope with anxiety, stress, and low moods by making them a personal, uplifting song: original lyrics written just for them, sung or rapped over a beat they pick.

> Anthem is a wellbeing tool, not a replacement for therapy or medical care. Crisis resources (988 Suicide & Crisis Lifeline; Crisis Text Line: text HOME to 741741) are linked on every page.

## How it works

```
Welcome → Check-in (name, age range, hobbies, feelings, message) → Beat + voice picker
       → Generating (breathing guide while the job runs) → Song (player, karaoke lyrics, download, remix)
```

1. **Safety screen.** If the user writes something in "What's going on?", the backend checks it with a local keyword list and a Claude classifier. If either flags it, the flow pauses with crisis resources. The user can continue, but their text is then left out of the song.
2. **Lyrics.** Claude writes verse / chorus / verse / chorus from the answers. The beat's genre and BPM set the style and a syllables-per-line target. The chorus is guaranteed to include "*Name*, you are amazing", and a profanity check triggers one retry.
3. **Vocals.** Each line is voiced separately by the vocal provider (ElevenLabs, or local TTS). Repeated chorus lines are recorded once.
4. **Mix.** The beat loops to fit. Every vocal line starts on a downbeat after a short intro, and lines that run long take an extra bar instead of being sped up. Choruses get a light double plus a tempo-synced echo. Vocals and beat are leveled, the mix is normalized with fades, and the result is exported as MP3.
5. **Remix.** "Try a different beat" reuses the same lyrics and recorded vocals and only re-runs the mix, so it costs no new API calls.

## Project layout

```
backend/            FastAPI app (Python 3.9+)
  app/main.py       HTTP routes
  app/jobs.py       In-process job queue (thread pool) + job state on disk
  app/safety.py     Free-text wellbeing screening (keywords + Claude)
  app/lyrics.py     Claude lyric generation, style/tempo fitting, checks
  app/vocals/       Swappable vocal providers: elevenlabs.py, local.py
  app/mixer.py      Beat looping, downbeat alignment, levels, fades, export
  app/cleanup.py    Deletes songs after RETENTION_HOURS (runs in-process; also CLI)
  tests/            Offline end-to-end tests (Claude stubbed, local TTS)
beats/
  beats.json        Beat manifest (id, name, category, bpm, key, mood, file, license, source_url)
  generate_beats.py Synthesizes the 15 placeholder loops (numpy, CC0)
  loops/            Loop audio (generated/ is gitignored and rebuilt by the script)
frontend/           Next.js 15 (App Router) + Tailwind v4
storage/            Generated songs and preview cache (gitignored, auto-deleted)
```

## Requirements

- **Python 3.9+** (3.11+ recommended)
- **Node.js 20+**
- **ffmpeg** for MP3 export: `brew install ffmpeg` (macOS) or `apt install ffmpeg`. Without it everything still works, but songs and previews are exported as WAV instead.
- For local/offline vocals: macOS (`say` is built in) or `espeak-ng` on Linux.

### API keys

| Key | Needed for | Where to get it |
|---|---|---|
| `ANTHROPIC_API_KEY` | Lyrics and wellbeing screening (required) | https://console.anthropic.com/settings/keys |
| `ELEVENLABS_API_KEY` | Natural-sounding vocals (optional; falls back to local TTS) | https://elevenlabs.io/app/settings/api-keys |

ElevenLabs licensing: free-tier output may not be used commercially and requires attribution. If you plan to offer Anthem publicly, or want users to share songs freely, use a paid ElevenLabs plan that grants commercial rights. The beats in this repo are CC0, and the lyrics are original Claude output generated for each user.

## Run locally

```bash
# 1. Config
cp .env.example .env            # then fill in ANTHROPIC_API_KEY (and ELEVENLABS_API_KEY if you have one)
cp frontend/.env.example frontend/.env.local

# 2. Beats (generates the 15 placeholder loops, ~2 seconds)
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
backend/.venv/bin/python beats/generate_beats.py

# 3. Backend: http://localhost:8000 (docs at /docs)
cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

# 4. Frontend: http://localhost:3000 (in a second terminal)
cd frontend && npm install && npm run dev
```

On startup the backend logs which vocal provider is active and whether MP3 export is available. `GET /health` reports the same.

### Tests

```bash
cd backend
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

The tests run fully offline. Claude is stubbed and vocals use local TTS. They cover the beat manifest, keyword screening, a full song plus remix (including bar alignment and the name-in-chorus guarantee), that free text never reaches disk, and 24-hour cleanup.

## Adding beats

1. Get a loop that is **8–16 bars** long, in 4/4, trimmed exactly on bar boundaries so it repeats cleanly. WAV is best (MP3 also works when ffmpeg is installed).
2. Check the license. Use only beats you made yourself, or loops marked **CC0** or explicitly **free for commercial use and redistribution**. On sites like Pixabay or Freesound, check each file's license; on Freesound, filter to CC0.
3. Put the file in `beats/loops/`, e.g. `beats/loops/pop-sunny-day.wav`.
4. Add an entry to the `beats` array in `beats/beats.json`:

```json
{
  "id": "pop-sunny-day",
  "name": "Sunny Day",
  "category": "pop",
  "bpm": 100,
  "key": "D major",
  "mood": "carefree",
  "bars": 8,
  "beats_per_bar": 4,
  "file": "loops/pop-sunny-day.wav",
  "license": "CC0-1.0",
  "source_url": "https://freesound.org/people/.../sounds/123456/"
}
```

- `category` must be one of `upbeat`, `chill`, `pop`, `rap`, `rock`.
- `bars` must match the file. The mixer derives the bar length from the file's duration divided by `bars`, so a wrong value misaligns the vocals.
- Optional `"feel": "halftime"` for trap-style beats (the vocals then pace at half the BPM).

The manifest is re-read automatically when it changes; there's no need to restart. Re-running `generate_beats.py` only rewrites its own generated entries and leaves hand-added beats alone.

## Vocal providers

Set `VOCAL_PROVIDER` to `elevenlabs`, `local`, or `auto`.

- **ElevenLabs** (`app/vocals/elevenlabs.py`): each lyric line goes through the text-to-speech API with neighbouring lines passed as context, so the delivery stays consistent. Voice expressiveness and speed are tuned per genre. The four UI voices (Warm, Bright, Deep, Smooth) map to ElevenLabs premade voices; to use any voices from your library, set `ELEVENLABS_VOICE_*`.
- **Local** (`app/vocals/local.py`): macOS `say` or `espeak-ng`. It's free and offline, but it sounds robotic. It's meant for development.

Text-to-speech speaks rhythmically; it doesn't sing a melody. It works well for rap and spoken-word delivery. For genuinely sung vocals, add a provider that subclasses `VocalProvider` in `app/vocals/base.py` (for example a singing-synthesis model) and register it in `app/vocals/__init__.py`. The rest of the pipeline doesn't change.

## Privacy & safety

- **No accounts.** Check-in answers stay in the browser tab (`sessionStorage`) until the user creates their song.
- **The free-text answer is never logged or saved.** It is used in memory for screening and lyric writing, then dropped. Job records on disk (`storage/jobs/<id>/job.json`) contain the name, beat, voice, and generated lyrics, but not the free text, feelings, or hobbies. A test asserts this.
- **Error logs** record only the exception type and Anthropic request IDs, never prompt or response content.
- **Songs are private.** They live under an unguessable ID with no listing endpoint, are served with `Cache-Control: private, no-store`, and are **deleted after 24 hours** (`RETENTION_HOURS`) by a cleanup thread in the API process. If you run several API processes, or prefer cron, also schedule `cd backend && .venv/bin/python -m app.cleanup`.
- **No analytics.** None is included. If you add some, keep sensitive inputs out of it.
- **Lyrics guardrails:** hopeful, age-appropriate (school-safe for 13–17), no profanity (instructed, then checked), nothing shaming, and only a brief acknowledgement of the struggle. User text is passed to Claude as clearly delimited context, never as instructions.
- **Claude calls** use `claude-opus-5-5` with structured JSON output and server-side refusal fallback enabled (`fallbacks: "default"`).

## Production notes

- **Job queue:** jobs run on an in-process thread pool (`MAX_WORKERS`), with state mirrored to disk. This is fine for a single server. To scale out, swap `submit_song` / `submit_remix` / `get` in `app/jobs.py` for RQ or Celery on Redis; the pipeline functions don't depend on the queue.
- **Rate limiting:** add per-IP rate limiting in front of `POST /songs` and `POST /screen` (each song makes 1–2 Claude calls and about 20 TTS calls).
- **Crisis resources** are US-focused (988, Crisis Text Line). The support page links to findahelpline.com for other countries. Localize these if you launch elsewhere.
