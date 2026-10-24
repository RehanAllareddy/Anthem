"""Delete generated songs after the retention window (24h by default).

On Vercel each job schedules its own deletion with a delayed queue message
(jobs._schedule_expiry), and the API sweeps opportunistically as a backstop.
Locally a background thread sweeps every CLEANUP_INTERVAL_MINUTES.

Run a sweep by hand (e.g. from cron):
    uv run python -m app.cleanup
"""
from __future__ import annotations

import logging
import threading
import time

from .config import get_settings
from .jobs import purge_expired

log = logging.getLogger(__name__)

_last_sweep = 0.0
_sweep_lock = threading.Lock()


def maybe_sweep() -> None:
    """Sweep at most once per cleanup interval per instance; never raises."""
    global _last_sweep
    interval = get_settings().cleanup_interval_minutes * 60
    if time.time() - _last_sweep < interval or not _sweep_lock.acquire(blocking=False):
        return
    try:
        _last_sweep = time.time()
        purge_expired()
    except Exception:  # noqa: BLE001 - cleanup must never break a user request
        log.exception("cleanup sweep failed")
    finally:
        _sweep_lock.release()


def start_background_cleanup() -> threading.Event:
    stop = threading.Event()
    interval = get_settings().cleanup_interval_minutes * 60

    def loop() -> None:
        while not stop.is_set():
            maybe_sweep()
            stop.wait(interval)

    threading.Thread(target=loop, name="cleanup", daemon=True).start()
    return stop


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"Removed {purge_expired()} expired song(s)")
