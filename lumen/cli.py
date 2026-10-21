from __future__ import annotations

import json

import click
from flask import current_app

from .catalog import DATA_DIR
from .entries import Entry, EntryRepository


def seed_entries(repository: EntryRepository, *, force: bool = False) -> int:
    """Add the sample entries from data/seed_entries.json. Skips titles a book already has."""
    raw = json.loads((DATA_DIR / "seed_entries.json").read_text(encoding="utf-8"))
    added = 0
    for item in raw:
        entry = Entry.from_dict(item)
        existing = {e.title for e in repository.list_for_book(entry.realm, entry.book)}
        if entry.title in existing and not force:
            continue
        repository.add(entry)
        added += 1
    return added


def register_cli(app) -> None:
    @app.cli.command("seed")
    @click.option("--force", is_flag=True, help="Add sample entries even if a title already exists.")
    def seed_command(force: bool) -> None:
        """Upload the sample entries to the configured storage (Vercel Blob or local)."""
        repository: EntryRepository = current_app.extensions["lumen.entries"]
        added = seed_entries(repository, force=force)
        click.echo(f"Seeded {added} entr{'y' if added == 1 else 'ies'} into {repository.store.name} storage.")
