"""Byte storage backends.

``BlobStore`` talks to Vercel Blob through the official ``vercel-blob`` SDK.
``LocalStore`` keeps the same layout on disk for local development and tests.
Both expose the same three operations, keyed by a slash-separated pathname.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Protocol

log = logging.getLogger(__name__)


class StorageError(Exception):
    """Storage failed for a reason other than a missing object."""


class NotFound(StorageError):
    """The requested pathname does not exist."""


class Store(Protocol):
    name: str

    def put(self, pathname: str, data: bytes, content_type: str) -> str: ...

    def get(self, pathname: str) -> bytes: ...

    def list(self, prefix: str) -> list[str]: ...


def _check_pathname(pathname: str) -> str:
    parts = pathname.split("/")
    if not pathname or pathname.startswith("/") or any(p in ("", ".", "..") for p in parts):
        raise StorageError(f"Invalid pathname: {pathname!r}")
    return pathname


class LocalStore:
    name = "local"

    def __init__(self, root: str | os.PathLike) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, pathname: str) -> Path:
        path = (self.root / _check_pathname(pathname)).resolve()
        if self.root not in path.parents:
            raise StorageError(f"Pathname escapes storage root: {pathname!r}")
        return path

    def put(self, pathname: str, data: bytes, content_type: str) -> str:
        path = self._path(pathname)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return pathname

    def get(self, pathname: str) -> bytes:
        path = self._path(pathname)
        if not path.is_file():
            raise NotFound(pathname)
        return path.read_bytes()

    def list(self, prefix: str) -> list[str]:
        base = self.root
        return sorted(
            p.relative_to(base).as_posix()
            for p in base.rglob("*")
            if p.is_file() and p.relative_to(base).as_posix().startswith(prefix)
        )

    def is_empty(self) -> bool:
        return not any(self.root.rglob("*.json"))


class BlobStore:
    """Vercel Blob via ``from vercel.blob import sync``.

    Credentials come from ``BLOB_READ_WRITE_TOKEN`` (added automatically when you
    connect a Blob store to the Vercel project, or by ``vercel env pull`` locally).
    ``access`` must match the store: "public" or "private".
    """

    name = "blob"

    def __init__(self, access: str = "public", cache_max_age: int = 60) -> None:
        from vercel.blob import sync as blob  # imported lazily so tests need no SDK

        if access not in ("public", "private"):
            raise ValueError("BLOB_ACCESS must be 'public' or 'private'")
        self._blob = blob
        self.access = access
        self.cache_max_age = cache_max_age

    def put(self, pathname: str, data: bytes, content_type: str) -> str:
        try:
            result = self._blob.put_blob(
                _check_pathname(pathname),
                data,
                access=self.access,
                content_type=content_type,
                add_random_suffix=False,
                allow_overwrite=True,
                cache_control_max_age=self.cache_max_age,
            )
        except self._blob.BlobError as exc:
            raise StorageError(str(exc)) from exc
        return result.pathname

    def get(self, pathname: str) -> bytes:
        try:
            return self._blob.get_blob(_check_pathname(pathname), access=self.access).body
        except self._blob.BlobNotFoundError as exc:
            raise NotFound(pathname) from exc
        except self._blob.BlobError as exc:
            raise StorageError(str(exc)) from exc

    def list(self, prefix: str) -> list[str]:
        try:
            return sorted(item.pathname for item in self._blob.query_blobs(prefix=prefix, page_size=1000))
        except self._blob.BlobError as exc:
            raise StorageError(str(exc)) from exc


def blob_configured() -> bool:
    return bool(
        os.environ.get("BLOB_READ_WRITE_TOKEN")
        or os.environ.get("VERCEL_BLOB_READ_WRITE_TOKEN")
        or os.environ.get("BLOB_STORE_ID")
    )


def make_store(backend: str, *, local_dir: str, blob_access: str) -> Store:
    """Pick a backend: "blob", "local", or "auto" (Blob when credentials exist)."""
    backend = (backend or "auto").lower()
    if backend == "auto":
        backend = "blob" if blob_configured() else "local"
    if backend == "blob":
        return BlobStore(access=blob_access)
    if backend == "local":
        if os.environ.get("VERCEL"):
            log.warning(
                "Using local storage on Vercel: entries are written to %s and will not persist. "
                "Connect a Vercel Blob store to the project.",
                local_dir,
            )
        return LocalStore(local_dir)
    raise ValueError(f"Unknown STORAGE_BACKEND: {backend!r}")
