"""Offline end-to-end tests: Claude is stubbed, vocals use the local provider,
storage is a temp directory, and tasks run on local threads."""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

P = "/api"  # API_PREFIX

FAKE_LYRICS = {
    "title": "Keep Shining",
    "verse1": [f"verse one line {i}" for i in range(8)],
    "chorus": ["you are brighter than you know", "every step is yours to take",
               "breathe in deep and let it go", "keep on going for your sake"],
    "verse2": [f"verse two line {i}" for i in range(8)],
}


@pytest.fixture()
def client(request, tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("TASK_BACKEND", "local")
    monkeypatch.setenv("VOCAL_PROVIDER", "local")
    monkeypatch.setenv("LYRICS_PROVIDER", getattr(request, "param", "claude"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-claude-is-stubbed")
    from app import config, storage, vocals

    def reset():
        config.get_settings.cache_clear()
        storage.get_storage.cache_clear()
        vocals.get_provider.cache_clear()

    reset()
    from app import lyrics, safety
    monkeypatch.setattr(lyrics, "claude_json", lambda **kw: FAKE_LYRICS)
    monkeypatch.setattr(safety, "claude_json", lambda **kw: {"flag": False, "category": "none"})

    from app.main import app
    with TestClient(app) as c:
        yield c
    reset()


def _wait(client, job_id, timeout=120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"{P}/songs/{job_id}").json()
        if body["status"] in ("done", "error"):
            return body
        time.sleep(0.3)
    raise AssertionError("job timed out")


def _song(client, **overrides):
    payload = {
        "name": "Maya", "age_range": "18-24", "hobbies": ["drawing", "soccer"],
        "feelings": ["stressed"], "messages": ["got_this"], "beat_id": "pop-brightside", "voice_id": "warm",
    }
    payload.update(overrides)
    r = client.post(f"{P}/songs", json=payload)
    assert r.status_code == 202, r.text
    return r.json()["job_id"]


def test_beats_manifest(client):
    data = client.get(f"{P}/beats").json()
    assert len(data["beats"]) >= 15
    for cat in data["categories"]:
        assert sum(b["category"] == cat for b in data["beats"]) >= 3
    r = client.get(P + data["beats"][0]["preview_url"])
    assert r.status_code == 200 and len(r.content) > 10_000


def test_routes_only_under_prefix(client):
    assert client.get("/beats").status_code == 404


def test_keyword_screen_flags_without_api(client):
    r = client.post(f"{P}/screen", json={"text": "honestly I want to die", "age_range": "13-17"}).json()
    assert r["flagged"] and r["resources"]
    r = client.post(f"{P}/screen", json={"text": "exams are stressing me out", "age_range": "13-17"}).json()
    assert not r["flagged"]


def test_song_end_to_end_and_remix(client):
    job_id = _song(client, free_text="finals week")
    song = _wait(client, job_id)
    assert song["status"] == "done", song
    # Name line is enforced into the chorus.
    assert any("Maya" in l for l in song["sections"][1]["lines"])
    starts = [t["start"] for t in song["timeline"]]
    assert starts == sorted(starts) and len(starts) == 24
    # Every line starts on a bar boundary.
    bar = 60 / 104 * 4
    for s in starts:
        assert abs(s / bar - round(s / bar)) < 0.01
    audio = client.get(P + song["audio_url"] + "?download=1")
    assert audio.status_code == 200 and "attachment" in audio.headers["content-disposition"]
    assert audio.headers["cache-control"] == "private, no-store"

    remix_id = client.post(f"{P}/songs/{job_id}/remix", json={"beat_id": "chill-rainy"}).json()["job_id"]
    remix = _wait(client, remix_id)
    assert remix["status"] == "done" and remix["sections"] == song["sections"]


def test_free_text_never_persisted(client, tmp_path):
    secret = "a very private sentence 12345"
    job_id = _song(client, name="Sam", beat_id="rap-cipher", free_text=secret)
    _wait(client, job_id)
    files = [f for f in tmp_path.rglob("*") if f.is_file()]
    assert files
    for f in files:
        assert secret.encode() not in f.read_bytes()


def test_redelivered_message_is_ignored_once_done(client):
    from app import jobs

    job_id = _song(client, beat_id="rock-garage")
    _wait(client, job_id)
    before = jobs.get(job_id)
    jobs.handle_message({"kind": "song", "job_id": job_id, "request": {}})  # duplicate delivery
    assert jobs.get(job_id) == before


def test_expire_message_and_sweep(client):
    from app import jobs

    job_id = _song(client, beat_id="upbeat-sunrise")
    _wait(client, job_id)
    assert abs(jobs.created_at(job_id) - time.time()) < 60
    jobs.handle_message({"kind": "expire", "job_id": job_id})
    assert client.get(f"{P}/songs/{job_id}").status_code == 404

    job_id = _song(client, beat_id="upbeat-sunrise")
    _wait(client, job_id)
    assert jobs.purge_expired(now=time.time() + 25 * 3600) >= 1
    assert client.get(f"{P}/songs/{job_id}").status_code == 404


def test_queue_subscriber_registered():
    from vercel.queue import get_subscriptions

    import app.worker  # noqa: F401
    from app.tasks import TOPIC

    assert any(s.topic == TOPIC for s in get_subscriptions())


def test_local_storage_rejects_escape(tmp_path):
    from app.storage import LocalStorage

    with pytest.raises(ValueError):
        LocalStorage(tmp_path).put("../outside.txt", b"x", "text/plain")


# ---------------------------------------------------------- template lyrics

@pytest.mark.parametrize("category", ["pop", "upbeat", "chill", "rap", "rock"])
@pytest.mark.parametrize("hobbies", [["drawing", "soccer"], ["drawing", "soccer", "my dog"]])
def test_templates_fill_every_placeholder(category, hobbies):
    from app.lyrics import has_profanity
    from app.templates import fill

    song = fill(category, "Maya", hobbies, "you've got this")
    lines = song["verse1"] + song["chorus"] + song["verse2"]
    assert len(song["verse1"]) == 8 and len(song["chorus"]) == 4 and len(song["verse2"]) == 8
    assert not any("{" in l or "}" in l for l in lines + [song["title"]])
    assert "Maya, you are amazing" in song["chorus"]
    for h in hobbies:
        assert any(h in l for l in lines), h
    assert not has_profanity(lines)


@pytest.mark.parametrize("client", ["template"], indirect=True)
def test_song_with_templates_needs_no_claude(client, monkeypatch):
    from app import lyrics, safety

    def boom(**kw):
        raise AssertionError("Claude should not be called in template mode")

    monkeypatch.setattr(lyrics, "claude_json", boom)
    monkeypatch.setattr(safety, "claude_json", boom)

    assert client.get(f"{P}/health").json()["lyrics"] == "template"
    r = client.post(f"{P}/screen", json={"text": "rough week at school", "age_range": "13-17"}).json()
    assert r["flagged"] is False and r["method"] == "keyword_only"

    song = _wait(client, _song(client, hobbies=["drawing", "soccer", "guitar"], messages=["amazing", "proud"]))
    assert song["status"] == "done", song
    lines = [l for s in song["sections"] for l in s["lines"]]
    assert "Maya, you are amazing" in song["sections"][1]["lines"]
    assert "Hear me say I'm proud of you" in song["sections"][1]["lines"]
    assert all(any(h in l for l in lines) for h in ("drawing", "soccer", "guitar"))


def test_profane_name_is_rejected(client):
    r = client.post(f"{P}/songs", json={
        "name": "shithead", "age_range": "18-24", "hobbies": ["a", "b"], "feelings": ["sad"], "beat_id": "pop-neon",
    })
    assert r.status_code == 422 and "kind and clean" in r.json()["detail"]
