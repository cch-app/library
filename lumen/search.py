"""Catalog search, the way a library terminal works: category, book name, title keyword."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .catalog import Catalog, Realm
from .entries import Entry

MAX_RESULTS = 60


@dataclass(frozen=True)
class SearchQuery:
    category: str = ""   # realm slug, "" for all realms
    book: str = ""       # "<realm>/<book>" slug, "" for all books
    keyword: str = ""    # words from a title

    @property
    def is_empty(self) -> bool:
        return not (self.category or self.book or self.keyword.strip())

    @property
    def words(self) -> list[str]:
        return [w for w in self.keyword.lower().split() if w]


@dataclass(frozen=True)
class SearchResult:
    kind: str  # "entry" | "book"
    title: str
    realm: Realm
    book_slug: str
    book_title: str
    published_at: datetime | None = None
    entry_count: int = 0
    page: int = 0  # page index of the entry inside its book (contents page is 0)

    @property
    def location(self) -> str:
        side = "left" if self.realm.side == "left" else "right"
        return f"Aisle {self.realm.pair + 1} · {side} shelf"


def _matches(words: list[str], *texts: str) -> bool:
    haystack = " ".join(texts).lower()
    return all(w in haystack for w in words)


def search_catalog(catalog: Catalog, entries: list[Entry], query: SearchQuery) -> list[SearchResult]:
    """Entries whose title (or book name) contains every keyword, newest first,
    followed by books whose name does. Category and book narrow both."""
    if query.is_empty:
        return []
    words = query.words

    def in_scope(realm_slug: str, book_slug: str) -> bool:
        if query.category and realm_slug != query.category:
            return False
        return not query.book or query.book == f"{realm_slug}/{book_slug}"

    # Page index of each entry inside its own book: newest entry is page 1.
    position: dict[str, int] = {}
    counts: dict[tuple[str, str], int] = {}
    for e in entries:  # already newest first
        key = (e.realm, e.book)
        counts[key] = counts.get(key, 0) + 1
        position[e.id + e.storage_key] = counts[key]

    results: list[SearchResult] = []
    for e in entries:
        realm, book = catalog.get_book(e.realm, e.book)
        if not book or not in_scope(realm.slug, book.slug) or not _matches(words, e.title, book.title):
            continue
        results.append(SearchResult(
            kind="entry", title=e.title, realm=realm, book_slug=book.slug, book_title=book.title,
            published_at=e.published_at, page=position[e.id + e.storage_key],
        ))
    for realm in catalog.realms:
        for book in realm.books:
            if in_scope(realm.slug, book.slug) and _matches(words, book.title):
                results.append(SearchResult(
                    kind="book", title=book.title, realm=realm, book_slug=book.slug, book_title=book.title,
                    entry_count=counts.get((realm.slug, book.slug), 0),
                ))
    return results[:MAX_RESULTS]
