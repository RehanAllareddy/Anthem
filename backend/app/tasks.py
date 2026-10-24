"""Runs background work for the API.

Messages are small dicts with a "kind" ("song", "remix", or "expire"); see
jobs.handle_message for what each does. Three modes (Settings.task_mode):

- "wait_until" (default on Vercel): the API function that created the job keeps
  running after it responds, via vercel.functions.wait_until, and generates the
  song itself. Bounded by the function's max duration (300 s by default).
- "queue" (TASK_BACKEND=vercel): publish to Vercel Queues; app/worker.py consumes.
- "local" (default elsewhere): a thread pool in this process.
"""
from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from .config import get_settings

log = logging.getLogger(__name__)

TOPIC = "echorie-songs"

# Song requests can carry the user's free-text answer, so keep them in the queue
# only as long as a generation attempt (plus retries) could need them.
SONG_MESSAGE_RETENTION_S = 15 * 60
MAX_RETENTION_S = 7 * 24 * 3600

_executor: Optional[ThreadPoolExecutor] = None


def _pool() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=get_settings().max_workers, thread_name_prefix="song")
    return _executor


def _handle(message: dict) -> None:
    from .jobs import handle_message  # local import avoids a cycle

    handle_message(message)


def dispatch(message: dict, *, delay_s: Optional[float] = None, retention_s: Optional[float] = None) -> None:
    """Start work for a message. In "wait_until" mode, call from the request's event loop."""
    mode = get_settings().task_mode

    if mode == "queue":
        from vercel.queue import sync as queue

        queue.send(
            TOPIC,
            message,
            idempotency_key=f"{message['kind']}-{message['job_id']}",
            delay=delay_s,
            retention=retention_s,
        )
        return

    if delay_s:
        # Delayed work is only used for expiry, which the retention sweep covers here.
        return

    if mode == "wait_until":
        from vercel.cache.context import get_context
        from vercel.functions import wait_until

        if get_context().wait_until is not None:
            wait_until(asyncio.to_thread(_handle, message))
            return
        # Without a wait_until hook the coroutine would be silently dropped and the
        # song would sit in "queued" forever; a thread is a best-effort fallback.
        log.warning("wait_until unavailable in this request; running job on a thread")

    _pool().submit(_handle, message)
