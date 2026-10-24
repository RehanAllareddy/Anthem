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
vercel.json         Vercel services: public Next.js frontend, internal FastAPI backend
frontend/           Next.js 15 (App Router) + Tailwind v4
  app/api/[...path] Proxies /api/* to the backend (BACKEND_URL service binding)
backend/            FastAPI app (Python 3.12, managed with uv)
  pyproject.toml    Dependencies + Vercel entrypoint, build script, queue subscriber
  app/main.py       HTTP routes, all under /api
  app/jobs.py       Job state, generation pipeline, expiry
  app/tasks.py      Runs jobs: wait_until on Vercel, threads locally, or Vercel Queues
  app/worker.py     Vercel Queues subscriber (only used with TASK_BACKEND=vercel)
  app/storage.py    Private Vercel Blob in production, ./storage on disk locally
  app/safety.py     Free-text wellbeing screening (keywords + Claude)
  app/lyrics.py     Claude lyric generation, style/tempo fitting, checks
  app/vocals/       Swappable vocal providers: elevenlabs.py, local.py
  app/mixer.py      Beat looping, downbeat alignment, levels, fades, MP3 export
  app/cleanup.py    Retention sweep (background thread locally; CLI)
  beats/
    beats.json        Beat manifest (id, name, category, bpm, key, mood, file, license, source_url)
    generate_beats.py Synthesizes the 15 placeholder loops (numpy, CC0)
    loops/            Loop audio (generated/ is gitignored; rebuilt by the script and the Vercel build)
  tests/            Offline end-to-end tests (Claude stubbed, local TTS)
storage/            Local-dev songs and job state (gitignored, auto-deleted)
```

## Requirements

- **Python 3.12** and **[uv](https://docs.astral.sh/uv/)** (`brew install uv`)
- **Node.js 20+**
- **ffmpeg** for MP3 export is bundled through the `imageio-ffmpeg` package, so nothing extra is needed. A system ffmpeg is used if one is installed.
- For local/offline vocals: macOS (`say` is built in) or `espeak-ng` on Linux.

### API keys

| Key | Needed for | Where to get it |
|---|---|---|
| `ANTHROPIC_API_KEY` | Original lyrics and wellbeing screening (optional; without it, template lyrics are used) | https://console.anthropic.com/settings/keys |
| `ELEVENLABS_API_KEY` | Natural-sounding vocals (optional; falls back to local TTS) | https://elevenlabs.io/app/settings/api-keys |

ElevenLabs licensing: free-tier output may not be used commercially and requires attribution. If you plan to offer Anthem publicly, or want users to share songs freely, use a paid ElevenLabs plan that grants commercial rights. The beats in this repo are CC0, and the lyrics are original Claude output generated for each user.

## Run locally

```bash
# 1. Config
cp .env.example .env            # then fill in ANTHROPIC_API_KEY (and ELEVENLABS_API_KEY if you have one)

# 2. Backend deps + beats (generates the 15 placeholder loops, ~2 seconds)
cd backend
uv sync
uv run python beats/generate_beats.py

# 3. Backend: http://localhost:8000 (docs at /docs, API under /api)
uv run uvicorn app.main:app --reload --port 8000

# 4. Frontend: http://localhost:3000 (in a second terminal)
cd frontend && npm install && npm run dev
```

The frontend's `/api/*` route proxies to `BACKEND_URL`, which defaults to `http://localhost:8000`, so the browser only ever talks to the frontend. Locally, songs run on background threads and are stored in `./storage`.

You can also run both services together with `vercel dev` from the repo root (Vercel CLI 48.1.8+), which injects `BACKEND_URL` through the service binding.

On startup the backend logs its vocal provider, storage, task runner, and whether MP3 export is available. `GET /api/health` reports some of the same.

### Tests

```bash
cd backend
uv run python -m pytest -q
```

The tests run fully offline: Claude is stubbed, vocals use local TTS, storage is a temp directory, and tasks run on threads. They cover:
- the beat manifest and that routes only answer under `/api`
- keyword screening
- a full song plus remix, including bar alignment and the name-in-chorus guarantee
- that free text never reaches storage
- that a redelivered queue message is ignored
- expiry by message and by sweep
- that the queue subscriber is registered

## Deploy on Vercel

`vercel.json` deploys one project with two services:

| Service | Root | Public? | Notes |
|---|---|---|---|
| `frontend` | `frontend/` | Yes, everything (`/(.*)`) | Next.js. Calls the backend from `app/api/[...path]/route.ts` through a binding that injects `BACKEND_URL`. |
| `backend` | `backend/` | No, internal only | FastAPI (`app.main:app`). Reachable only through the frontend's binding. Also deploys the queue subscriber in `app/worker.py`. |

How generation runs on Vercel:
1. `POST /api/songs` saves a "queued" job state to Blob and responds right away.
2. The same function keeps running after the response (`vercel.functions.wait_until`). It writes the lyrics, records the vocals, mixes the song, and saves it to Blob, updating the job state as it goes. This must finish within the function's max duration, 300 s by default; a song takes about a minute.
3. The browser polls `/api/songs/<id>`. Each poll reads the newest state snapshot from Blob, so it works on any instance.
4. Songs older than `RETENTION_HOURS` are deleted by a sweep that runs at most every `CLEANUP_INTERVAL_MINUTES` per instance, triggered by song requests and status polls.

To use Vercel Queues instead (durable, with retries), set `TASK_BACKEND=vercel`. Generation then runs in the subscriber in `app/worker.py`, and each song schedules its own deletion with a delayed message.

Setup:
1. **Create a Blob store** (Storage tab → Blob), choose **Private** access, and connect it to the project. This adds `BLOB_STORE_ID`, and the backend authenticates with OIDC.
2. **Add environment variables:** `ELEVENLABS_API_KEY` (required on Vercel, because `say` and `espeak` aren't available there), plus `ANTHROPIC_API_KEY` if you want Claude-written lyrics instead of templates.
3. **Deploy** with `vercel deploy` or by pushing to a connected Git repo. The backend build (`[tool.vercel.scripts] build` in `backend/pyproject.toml`) generates the beat loops into the bundle.

Notes:
- **Queues and services are in beta** on Vercel. Queue messages are pinned to the deployment that published them, so an old deployment keeps processing (and expiring) its own songs until those messages are done.
- Generation should take well under the default 300 s function limit. If you use longer songs or slower voices, raise it.
- Each song makes about 20 TTS calls and 1–2 Claude calls, plus roughly 15–25 Blob writes and a Blob list and read per status poll.

## Adding beats

1. Get a loop that is **8–16 bars** long, in 4/4, trimmed exactly on bar boundaries so it repeats cleanly. WAV is best (MP3 also works when ffmpeg is installed).
2. Check the license. Use only beats you made yourself, or loops marked **CC0** or explicitly **free for commercial use and redistribution**. On sites like Pixabay or Freesound, check each file's license; on Freesound, filter to CC0.
3. Put the file in `backend/beats/loops/`, e.g. `backend/beats/loops/pop-sunny-day.wav`, and commit it.
4. Add an entry to the `beats` array in `backend/beats/beats.json`:

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

## Lyrics: Claude or templates

`LYRICS_PROVIDER` is `auto` by default: Claude when `ANTHROPIC_API_KEY` is set, templates otherwise. Set it to `claude` or `template` to choose explicitly.

- **Claude:** writes original lyrics for every song from all the check-in answers, and screens the "what's going on?" answer.
- **Templates** (`backend/app/templates.py`): one fixed song per genre (pop, upbeat, chill, rap, rock). Each song fills in the listener's name, first two or three hobbies, and one chosen message ("Hear me say I'm proud of you"); the chorus always includes "*Name*, you are amazing". This mode is free and instant, but every song in a genre has the same lines. The free-text answer goes through the **keyword check only**, which catches direct phrases ("want to die", "hurt myself") but can miss indirect ones. To change the words, edit the templates. Keep hobbies in phrasings that work with any noun ("lost in {hobby1}", "from {hobby1} to {hobby2}").

Names, hobbies, and custom messages are checked for profanity before a song starts, because they go straight into the lyrics.

## Vocal providers

Set `VOCAL_PROVIDER` to `elevenlabs`, `local`, or `auto`.

- **ElevenLabs** (`app/vocals/elevenlabs.py`): each lyric line goes through the text-to-speech API on its own. Neighbouring lines aren't sent as context, because ElevenLabs then sometimes speaks a fragment of the next line at the end of a clip. Voice expressiveness and speed are tuned per genre. The three UI voices (Warm, Bright, Deep) are set with `ELEVENLABS_VOICE_WARM`, `_BRIGHT`, and `_DEEP`. On the free plan, use voices you designed or the account's default voices: free accounts can't use Voice Library voices through the API.
- **Local** (`app/vocals/local.py`): macOS `say` or `espeak-ng`. It's free and offline, but it sounds robotic. It's meant for development.

Text-to-speech speaks rhythmically; it doesn't sing a melody. It works well for rap and spoken-word delivery. For genuinely sung vocals, add a provider that subclasses `VocalProvider` in `app/vocals/base.py` (for example a singing-synthesis model) and register it in `app/vocals/__init__.py`. The rest of the pipeline doesn't change.

## Privacy & safety

- **No accounts.** Check-in answers stay in the browser tab (`sessionStorage`) until the user creates their song.
- **The free-text answer is never logged or saved.** It is used for screening and lyric writing, then dropped. On Vercel it travels to the worker inside the queue message, which is set to expire after 15 minutes. Stored job state contains the name, beat, voice, and generated lyrics, but not the free text, feelings, or hobbies. A test asserts this.
- **Error logs** record only the exception type and Anthropic request IDs, never prompt or response content.
- **Songs are private.** They're stored in a private Blob store (on disk locally) under an unguessable ID, with no listing endpoint. They're served only through the API with `Cache-Control: private, no-store`, and the backend itself has no public route. They are **deleted after 24 hours** (`RETENTION_HOURS`): on Vercel by a delayed queue message plus a sweep, and locally by a cleanup thread. To sweep by hand: `cd backend && uv run python -m app.cleanup`.
- **No analytics.** None is included. If you add some, keep sensitive inputs out of it.
- **Lyrics guardrails:** hopeful, age-appropriate (school-safe for 13–17), no profanity (instructed, then checked), nothing shaming, and only a brief acknowledgement of the struggle. User text is passed to Claude as clearly delimited context, never as instructions.
- **Claude calls** use `claude-opus-5-5` with structured JSON output and server-side refusal fallback enabled (`fallbacks: "default"`).

## Production notes

- **Rate limiting:** add per-IP rate limiting in front of `POST /songs` and `POST /screen` (each song makes 1–2 Claude calls and about 20 TTS calls).
- **Crisis resources** are US-focused (988, Crisis Text Line). The support page links to findahelpline.com for other countries. Localize these if you launch elsewhere.
