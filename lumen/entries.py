"""Entries: the dated articles and posts inside each book.

Every entry is one JSON object in storage:

    entries/<realm>/<book>/<YYYYmmddTHHMMSS>-<slug>-<id>.json

Uploaded images live beside them under ``media/<realm>/<book>/``.
"""

from __future__ import annotations

import json
import math
import mimetypes
import secrets
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from .catalog import slugify
from .storage import NotFound, Store

ENTRY_PREFIX = "entries/"
MEDIA_PREFIX = "media/"
WORDS_PER_MINUTE = 200

IMAGE_TYPES = {
    "image/png": (".png", b"\x89PNG\r\n\x1a\n"),
    "image/jpeg": (".jpg", b"\xff\xd8\xff"),
    "image/gif": (".gif", b"GIF8"),
    "image/webp": (".webp", b"RIFF"),
}


@dataclass
class Entry:
    realm: str
    book: str
    title: str
    author: str
    body: str
    published_at: datetime
    id: str = field(default_factory=lambda: secrets.token_hex(4))
    image_path: str | None = None  # pathname in storage (uploaded image)
    image_url: str | None = None   # static or external image
    image_alt: str = ""
    caption: str = ""

    @property
    def paragraphs(self) -> list[str]:
        return [p.strip() for p in self.body.replace("\r\n", "\n").split("\n\n") if p.strip()]

    @property
    def read_minutes(self) -> int:
        return max(1, math.ceil(len(self.body.split()) / WORDS_PER_MINUTE))

    @property
    def date_label(self) -> str:
        d = self.published_at
        return f"{d.strftime('%b')} {d.day}, {d.year}"

    @property
    def storage_key(self) -> str:
        stamp = self.published_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S")
        return f"{ENTRY_PREFIX}{self.realm}/{self.book}/{stamp}-{slugify(self.title)[:60]}-{self.id}.json"

    def to_json(self) -> bytes:
        data = asdict(self)
        data["published_at"] = self.published_at.isoformat()
        return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

    @classmethod
    def from_dict(cls, data: dict) -> "Entry":
        published = datetime.fromisoformat(data["published_at"])
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        return cls(
            realm=data["realm"],
            book=data["book"],
            title=data["title"],
            author=data.get("author") or "Anonymous",
            body=data["body"],
            published_at=published,
            id=data.get("id") or secrets.token_hex(4),
            image_path=data.get("image_path"),
            image_url=data.get("image_url"),
            image_alt=data.get("image_alt", ""),
            caption=data.get("caption", ""),
        )


class EntryRepository:
    """Reads and writes entries, with a short in-process cache.

    On Vercel a warm function instance reuses this cache between requests, which
    keeps Blob list/get calls down. Writes clear it.
    """

    def __init__(self, store: Store, cache_ttl: float = 30.0) -> None:
        self.store = store
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[float, object]] = {}
        self._lock = threading.Lock()

    # -- cache -------------------------------------------------------------
    def _cached(self, key: str, loader):
        now = time.monotonic()
        with self._lock:
            hit = self._cache.get(key)
            if hit and now - hit[0] < self.cache_ttl:
                return hit[1]
        value = loader()
        with self._lock:
            self._cache[key] = (now, value)
        return value

    def clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()

    # -- reads -------------------------------------------------------------
    def list_for_book(self, realm: str, book: str) -> list[Entry]:
        """All entries in a book, newest first."""

        def load() -> list[Entry]:
            entries = []
            for key in self.store.list(f"{ENTRY_PREFIX}{realm}/{book}/"):
                if not key.endswith(".json"):
                    continue
                try:
                    entries.append(Entry.from_dict(json.loads(self.store.get(key))))
                except (NotFound, ValueError, KeyError):
                    continue
            return sorted(entries, key=lambda e: e.published_at, reverse=True)

        return self._cached(f"book:{realm}/{book}", load)

    def all_entries(self) -> list[Entry]:
        """Every entry in the library, newest first (used by catalog search)."""

        def load() -> list[Entry]:
            entries = []
            for key in self.store.list(ENTRY_PREFIX):
                if not key.endswith(".json"):
                    continue
                try:
                    entries.append(Entry.from_dict(json.loads(self.store.get(key))))
                except (NotFound, ValueError, KeyError):
                    continue
            return sorted(entries, key=lambda e: e.published_at, reverse=True)

        return self._cached("all", load)

    def counts(self) -> dict[tuple[str, str], int]:
        """Number of entries per (realm, book), from one listing call."""

        def load() -> dict[tuple[str, str], int]:
            counts: dict[tuple[str, str], int] = {}
            for key in self.store.list(ENTRY_PREFIX):
                parts = key[len(ENTRY_PREFIX):].split("/")
                if len(parts) == 3 and parts[2].endswith(".json"):
                    counts[(parts[0], parts[1])] = counts.get((parts[0], parts[1]), 0) + 1
            return counts

        return self._cached("counts", load)

    def read_media(self, pathname: str) -> tuple[bytes, str]:
        if not pathname.startswith(MEDIA_PREFIX):
            raise NotFound(pathname)
        content_type = mimetypes.guess_type(pathname)[0] or "application/octet-stream"
        return self.store.get(pathname), content_type

    # -- writes ------------------------------------------------------------
    def add(self, entry: Entry) -> str:
        key = self.store.put(entry.storage_key, entry.to_json(), "application/json")
        self.clear_cache()
        return key

    def save_image(self, realm: str, book: str, data: bytes, content_type: str) -> str:
        ext, _ = IMAGE_TYPES[content_type]
        pathname = f"{MEDIA_PREFIX}{realm}/{book}/{secrets.token_hex(8)}{ext}"
        return self.store.put(pathname, data, content_type)


def sniff_image(data: bytes) -> str | None:
    """Return the image MIME type from magic bytes, or None if not an allowed image."""
    for content_type, (_, magic) in IMAGE_TYPES.items():
        if data.startswith(magic):
            if content_type == "image/webp" and data[8:12] != b"WEBP":
                continue
            return content_type
    return None


# -- book layout -------------------------------------------------------------
@dataclass
class BookPage:
    kind: str  # "toc" | "entry" | "end"
    number: int
    entry: Entry | None = None


def build_pages(entries: list[Entry]) -> list[BookPage]:
    """Contents page, one page per entry (newest first), then a closing page."""
    pages = [BookPage(kind="toc", number=1)]
    pages += [BookPage(kind="entry", number=i + 2, entry=e) for i, e in enumerate(entries)]
    pages.append(BookPage(kind="end", number=len(pages) + 1))
    return pages


def build_leaves(pages: list[BookPage]) -> list[tuple[BookPage, BookPage | None]]:
    """Group pages into physical leaves for the page-turn view.

    Page 0 (contents) sits on the left board. Leaf k carries page 2k+1 on its
    front (right-hand side) and page 2k+2 on its back (left-hand side once turned).
    """
    count = math.ceil((len(pages) - 1) / 2)
    return [
        (pages[2 * k + 1], pages[2 * k + 2] if 2 * k + 2 < len(pages) else None)
        for k in range(count)
    ]
