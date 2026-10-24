"""Object storage for job state, vocal clips, and finished songs.

Production uses a *private* Vercel Blob store, so audio is only reachable through
this API. Local development uses a directory on disk. Both expose the same small
interface, keyed by slash-separated paths like "jobs/<id>/song.mp3".

Blob objects are written once and never overwritten: overwritten blobs can be
served stale from the CDN, so job state is stored as a series of snapshots and
readers take the newest one (see jobs.py).
"""
from __future__ import annotations

import logging
import shutil
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from .config import get_settings

log = logging.getLogger(__name__)


class Storage(ABC):
    name: str

    @abstractmethod
    def put(self, path: str, data: bytes, content_type: str) -> None: ...

    @abstractmethod
    def get(self, path: str) -> Optional[bytes]:
        """Return the object's bytes, or None if it doesn't exist."""

    @abstractmethod
    def list(self, prefix: str) -> List[str]:
        """Paths of all objects under prefix (recursive)."""

    @abstractmethod
    def folders(self, prefix: str) -> List[str]:
        """Names of the immediate sub-folders of prefix (which must end with "/")."""

    @abstractmethod
    def delete_prefix(self, prefix: str) -> None: ...


class LocalStorage(Storage):
    name = "local"

    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)

    def _path(self, path: str) -> Path:
        p = (self.root / path).resolve()
        if self.root.resolve() not in p.parents and p != self.root.resolve():
            raise ValueError("path escapes storage root")
        return p

    def put(self, path: str, data: bytes, content_type: str) -> None:
        p = self._path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(p)

    def get(self, path: str) -> Optional[bytes]:
        p = self._path(path)
        return p.read_bytes() if p.is_file() else None

    def list(self, prefix: str) -> List[str]:
        base = self._path(prefix.rstrip("/")) if prefix.rstrip("/") else self.root
        if not base.exists():
            return []
        return sorted(str(f.relative_to(self.root)) for f in base.rglob("*") if f.is_file() and not f.name.endswith(".tmp"))

    def folders(self, prefix: str) -> List[str]:
        base = self._path(prefix.rstrip("/"))
        return sorted(d.name for d in base.iterdir() if d.is_dir()) if base.exists() else []

    def delete_prefix(self, prefix: str) -> None:
        shutil.rmtree(self._path(prefix.rstrip("/")), ignore_errors=True)


class BlobStorage(Storage):
    """Private Vercel Blob store. Credentials come from the connected store
    (BLOB_STORE_ID + OIDC on Vercel) or BLOB_READ_WRITE_TOKEN."""

    name = "blob"

    def __init__(self) -> None:
        from vercel.blob import sync as blob

        self._blob = blob

    def put(self, path: str, data: bytes, content_type: str) -> None:
        self._blob.put_blob(path, data, access="private", content_type=content_type, cache_control_max_age=60)

    def get(self, path: str) -> Optional[bytes]:
        try:
            return self._blob.get_blob(path, access="private").body
        except self._blob.BlobNotFoundError:
            return None

    def list(self, prefix: str) -> List[str]:
        return sorted(item.pathname for item in self._blob.query_blobs(prefix=prefix))

    def folders(self, prefix: str) -> List[str]:
        out = []
        for entry in self._blob.query_blob_entries(prefix=prefix):
            if isinstance(entry, self._blob.BlobPrefix):
                out.append(entry.prefix[len(prefix):].rstrip("/"))
        return sorted(out)

    def delete_prefix(self, prefix: str) -> None:
        paths = self.list(prefix)
        for i in range(0, len(paths), 1000):
            self._blob.delete_blob(paths[i : i + 1000])


@lru_cache
def get_storage() -> Storage:
    s = get_settings()
    if s.use_blob:
        return BlobStorage()
    if s.storage_backend == "auto" and s.use_vercel_queues:
        log.warning("No Blob store connected: songs are stored on this instance only and may 404 on other instances")
    return LocalStorage(s.storage_dir)
