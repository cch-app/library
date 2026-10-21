"""The fixed catalog of realms (bookshelves) and books (topics).

Realms and book titles live in ``data/catalog.json`` and ship with the code.
Entries (the pages inside each book) are dynamic and live in storage; see
``lumen.entries``.
"""

from __future__ import annotations

import json
import random
import re
import unicodedata
import zlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Leather tones used for book spines; all are dark enough for cream text.
LEATHER = (
    "#6B2E2E", "#2E4A6B", "#3E5B3A", "#6B5A2E", "#4A2E6B",
    "#2E5B5B", "#7A4A22", "#3A3F5C", "#5C2E45", "#4F4A2A",
)


def slugify(text: str) -> str:
    """Turn a title into a URL-safe slug: "Bayes' theorem" -> "bayes-theorem"."""
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return slug or "untitled"


@dataclass(frozen=True)
class Spine:
    width: int
    height: int
    color: str


@dataclass(frozen=True)
class Book:
    slug: str
    title: str
    realm_slug: str
    intro: str | None
    spine: Spine


@dataclass(frozen=True)
class Realm:
    slug: str
    name: str
    color: str
    blurb: str
    index: int
    books: tuple[Book, ...]
    # Decorative rows of tiny spines drawn on the 3D shelf in the aisle.
    shelf_rows: tuple[tuple[Spine, ...], ...]

    @property
    def side(self) -> str:
        return "left" if self.index % 2 == 0 else "right"

    @property
    def pair(self) -> int:
        """Which step of the aisle this shelf stands at (two shelves per step)."""
        return self.index // 2

    def get_book(self, slug: str) -> Book | None:
        return next((b for b in self.books if b.slug == slug), None)


@dataclass(frozen=True)
class Catalog:
    realms: tuple[Realm, ...]

    @property
    def station_count(self) -> int:
        return (len(self.realms) + 1) // 2

    def get_realm(self, slug: str) -> Realm | None:
        return next((r for r in self.realms if r.slug == slug), None)

    def get_book(self, realm_slug: str, book_slug: str) -> tuple[Realm, Book] | tuple[None, None]:
        realm = self.get_realm(realm_slug)
        book = realm.get_book(book_slug) if realm else None
        return (realm, book) if book else (None, None)


def _rng(key: str) -> random.Random:
    return random.Random(zlib.crc32(key.encode()))


def _book_spine(key: str) -> Spine:
    rng = _rng(key)
    return Spine(width=40 + rng.randint(0, 18), height=150 + rng.randint(0, 34), color=rng.choice(LEATHER))


def _shelf_rows(key: str, rows: int = 4, per_row: int = 22) -> tuple[tuple[Spine, ...], ...]:
    rng = _rng("shelf:" + key)
    return tuple(
        tuple(
            Spine(width=8 + rng.randint(0, 8), height=58 + rng.randint(0, 34), color=rng.choice(LEATHER))
            for _ in range(per_row)
        )
        for _ in range(rows)
    )


def build_catalog(raw: dict) -> Catalog:
    intros: dict[str, str] = raw.get("book_intros", {})
    realms = []
    for index, r in enumerate(raw["realms"]):
        books = tuple(
            Book(
                slug=slugify(title),
                title=title,
                realm_slug=r["slug"],
                intro=intros.get(f"{r['slug']}/{slugify(title)}"),
                spine=_book_spine(f"{r['slug']}/{title}"),
            )
            for title in r["books"]
        )
        realms.append(
            Realm(
                slug=r["slug"],
                name=r["name"],
                color=r["color"],
                blurb=r["blurb"],
                index=index,
                books=books,
                shelf_rows=_shelf_rows(r["slug"]),
            )
        )
    return Catalog(realms=tuple(realms))


@lru_cache(maxsize=4)
def load_catalog(path: str | None = None) -> Catalog:
    file = Path(path) if path else DATA_DIR / "catalog.json"
    return build_catalog(json.loads(file.read_text(encoding="utf-8")))
