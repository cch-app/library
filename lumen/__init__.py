"""Lumen Archive: a game-like library of knowledge from every field."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask

from .catalog import load_catalog
from .cli import register_cli, seed_entries
from .entries import EntryRepository
from .storage import LocalStore, make_store

ROOT = Path(__file__).resolve().parent.parent
PUBLIC_STATIC = ROOT / "public" / "static"


def create_app(test_config: dict | None = None) -> Flask:
    # On Vercel, files in public/ are served by the CDN. Pointing Flask's static
    # folder at the same place makes `flask run` serve them locally too.
    app = Flask(__name__, static_folder=str(PUBLIC_STATIC), static_url_path="/static")

    on_vercel = bool(os.environ.get("VERCEL"))
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        STORAGE_BACKEND=os.environ.get("STORAGE_BACKEND", "auto"),
        LOCAL_STORAGE_DIR=os.environ.get(
            "LOCAL_STORAGE_DIR", "/tmp/lumen-archive" if on_vercel else str(ROOT / ".data")
        ),
        BLOB_ACCESS=os.environ.get("BLOB_ACCESS", "public"),
        WRITE_PASSCODE=os.environ.get("WRITE_PASSCODE") or None,
        CACHE_TTL=float(os.environ.get("CACHE_TTL", "30")),
        MAX_CONTENT_LENGTH=int(4.5 * 1024 * 1024),
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=on_vercel,
        ASSET_VERSION=os.environ.get("VERCEL_GIT_COMMIT_SHA", "dev")[:8],
    )
    if test_config:
        app.config.update(test_config)

    if on_vercel and app.config["SECRET_KEY"] == "dev-only-change-me":
        app.logger.warning("SECRET_KEY is not set; set it in the Vercel project settings.")

    store = make_store(
        app.config["STORAGE_BACKEND"],
        local_dir=app.config["LOCAL_STORAGE_DIR"],
        blob_access=app.config["BLOB_ACCESS"],
    )
    repository = EntryRepository(store, cache_ttl=app.config["CACHE_TTL"])
    app.extensions["lumen.catalog"] = load_catalog()
    app.extensions["lumen.entries"] = repository

    # A fresh local store gets the sample entries so the demo book isn't empty.
    if isinstance(store, LocalStore) and store.is_empty() and not app.config.get("SKIP_AUTO_SEED"):
        seed_entries(repository)

    from .routes import bp

    app.register_blueprint(bp)
    register_cli(app)
    return app
