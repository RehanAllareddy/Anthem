"""Offline end-to-end tests: Claude is stubbed, vocals use the local provider."""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

FAKE_LYRICS = {
    "title": "Keep Shining",
    "verse1": [f"verse one line {i}" for i in range(8)],
    "chorus": ["you are brighter than you know", "every step is yours to take",
               "breathe in deep and let it go", "keep on going for your sake"],
    "verse2": [f"verse two line {i}" for i in range(8)],
}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("VOCAL_PROVIDER", "local")
    from app import config, vocals
    config.get_settings.cache_clear()
    vocals.get_provider.cache_clear()

    from app import lyrics, safety
    monkeypatch.setattr(lyrics, "claude_json", lambda **kw: FAKE_LYRICS)
    monkeypatch.setattr(safety, "claude_json", lambda **kw: {"flag": False, "category": "none"})

    from app.main import app
    with TestClient(app) as c:
        yield c
    config.get_settings.cache_clear()
    vocals.get_provider.cache_clear()


def _wait(client, job_id, timeout=120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/songs/{job_id}").json()
        if body["status"] in ("done", "error"):
            return body
        time.sleep(0.3)
    raise AssertionError("job timed out")


def test_beats_manifest(client):
    data = client.get("/beats").json()
    assert len(data["beats"]) >= 15
    for cat in data["categories"]:
        assert sum(b["category"] == cat for b in data["beats"]) >= 3
    r = client.get(data["beats"][0]["preview_url"])
    assert r.status_code == 200 and len(r.content) > 10_000


def test_keyword_screen_flags_without_api(client):
    r = client.post("/screen", json={"text": "honestly I want to die", "age_range": "13-17"}).json()
    assert r["flagged"] and r["resources"]
    r = client.post("/screen", json={"text": "exams are stressing me out", "age_range": "13-17"}).json()
    assert not r["flagged"]


def test_song_end_to_end_and_remix(client):
    payload = {
        "name": "Maya", "age_range": "18-24", "hobbies": ["drawing", "soccer"],
        "feelings": ["stressed"], "messages": ["got_this"], "beat_id": "pop-brightside",
        "voice_id": "warm", "free_text": "finals week",
    }
    job_id = client.post("/songs", json=payload).json()["job_id"]
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
    audio = client.get(song["audio_url"] + "?download=1")
    assert audio.status_code == 200 and "attachment" in audio.headers["content-disposition"]

    remix_id = client.post(f"/songs/{job_id}/remix", json={"beat_id": "chill-rainy"}).json()["job_id"]
    remix = _wait(client, remix_id)
    assert remix["status"] == "done" and remix["sections"] == song["sections"]


def test_free_text_never_persisted(client, tmp_path):
    secret = "a very private sentence 12345"
    payload = {
        "name": "Sam", "age_range": "25+", "hobbies": ["cooking", "hiking"],
        "feelings": ["anxious"], "messages": [], "beat_id": "rap-cipher", "free_text": secret,
    }
    job_id = client.post("/songs", json=payload).json()["job_id"]
    _wait(client, job_id)
    for f in tmp_path.rglob("*.json"):
        assert secret not in f.read_text()


def test_cleanup_removes_expired(client):
    from app import cleanup, jobs
    payload = {
        "name": "Lee", "age_range": "25+", "hobbies": ["chess", "running"],
        "feelings": ["lonely"], "beat_id": "rock-garage",
    }
    job_id = client.post("/songs", json=payload).json()["job_id"]
    _wait(client, job_id)
    assert cleanup.purge_expired(now=time.time() + 25 * 3600) >= 1
    assert not jobs.job_dir(job_id).exists()
    assert client.get(f"/songs/{job_id}").status_code == 404
