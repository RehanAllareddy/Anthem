"""Delete generated songs after the retention window (24h by default).

Runs automatically inside the API process. Can also be run on its own, e.g. from cron:
    python -m app.cleanup
"""
from __future__ import annotations

import json
import logging
import shutil
import threading
import time
from typing import Optional

from . import jobs
from .config import get_settings

log = logging.getLogger(__name__)


def purge_expired(now: Optional[float] = None) -> int:
    s = get_settings()
    now = now or time.time()
    cutoff = now - s.retention_hours * 3600
    removed = 0
    for d in s.jobs_dir.iterdir() if s.jobs_dir.exists() else []:
        if not d.is_dir():
            continue
        created = d.stat().st_mtime
        meta = d / "job.json"
        if meta.exists():
            try:
                created = json.loads(meta.read_text()).get("created_at", created)
            except (json.JSONDecodeError, OSError):
                pass
        if created < cutoff:
            shutil.rmtree(d, ignore_errors=True)
            jobs.forget(d.name)
            removed += 1
    if removed:
        log.info("cleanup: removed %d expired song(s)", removed)
    return removed


def start_background_cleanup() -> threading.Event:
    stop = threading.Event()
    interval = get_settings().cleanup_interval_minutes * 60

    def loop() -> None:
        while not stop.is_set():
            try:
                purge_expired()
            except Exception:  # noqa: BLE001 - never let cleanup kill the thread
                log.exception("cleanup failed")
            stop.wait(interval)

    threading.Thread(target=loop, name="cleanup", daemon=True).start()
    return stop


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"Removed {purge_expired()} expired song(s)")
