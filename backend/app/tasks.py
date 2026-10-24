"""Dispatches background work: Vercel Queues in production, threads locally.

Messages are small dicts with a "kind" ("song", "remix", or "expire"); see
jobs.handle_message for what each does.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from .config import get_settings

log = logging.getLogger(__name__)

TOPIC = "anthem-songs"

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


def enqueue(message: dict, *, delay_s: Optional[float] = None, retention_s: Optional[float] = None) -> None:
    if get_settings().use_vercel_queues:
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
        # Delayed work is only used for expiry; locally the cleanup thread covers it.
        return
    from .jobs import handle_message

    _pool().submit(handle_message, message)
