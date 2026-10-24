"""Vercel Queues subscriber that runs song generation and expiry.

Registered in pyproject.toml under [[tool.vercel.subscribers]]; Vercel turns it
into a private, queue-triggered function with no public URL. Locally, tasks.py
calls jobs.handle_message on a thread instead, so this module isn't used.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from vercel.queue import Message, subscribe

from .jobs import handle_message
from .tasks import TOPIC

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


# handle_message records failures on the job itself, so a raised exception here
# means something unexpected (e.g. storage outage); retry a couple of times.
@subscribe(topic=TOPIC, retry_after=30, max_attempts=3)
async def process(message: Message[Dict[str, Any]]) -> None:
    # The pipeline is synchronous (pydub, httpx, Blob sync API); keep it off the event loop.
    await asyncio.to_thread(handle_message, message.payload)
