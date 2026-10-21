from __future__ import annotations

import hmac
import secrets
from datetime import datetime, timezone

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .entries import Entry, EntryRepository, build_leaves, build_pages, sniff_image
from .storage import NotFound, StorageError

bp = Blueprint("main", __name__)

MAX_TITLE = 120
MAX_AUTHOR = 60
MAX_BODY = 6000
MAX_IMAGE_BYTES = 4 * 1024 * 1024  # Vercel Functions accept request bodies up to 4.5 MB


def catalog():
    return current_app.extensions["lumen.catalog"]


def repo() -> EntryRepository:
    return current_app.extensions["lumen.entries"]


def csrf_token() -> str:
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


@bp.app_context_processor
def inject_globals():
    return {"csrf_token": csrf_token}


# -- pages ---------------------------------------------------------------------
@bp.get("/")
def gate():
    """Landing page: the door into the library."""
    return render_template("gate.html", returning=request.args.get("from") == "library")


@bp.get("/realms")
def aisle():
    """The aisle of bookshelves, one shelf per realm."""
    cat = catalog()
    open_realm = cat.get_realm(request.args.get("shelf", ""))
    highlight = request.args.get("book", "") if open_realm else ""
    try:
        counts = repo().counts()
    except StorageError:
        current_app.logger.exception("Could not list entries")
        counts = {}
    return render_template(
        "aisle.html",
        catalog=cat,
        counts=counts,
        open_realm=open_realm,
        highlight=highlight,
        arriving=request.args.get("from") == "gate",
    )


@bp.get("/realms/<realm_slug>/<book_slug>")
def book(realm_slug: str, book_slug: str):
    """One book: its entries as pages, newest first, with page turning."""
    realm, book = catalog().get_book(realm_slug, book_slug)
    if not book:
        abort(404)
    try:
        entries = repo().list_for_book(realm.slug, book.slug)
    except StorageError:
        current_app.logger.exception("Could not load entries")
        entries = []
    pages = build_pages(entries)
    return render_template(
        "book.html",
        realm=realm,
        book=book,
        pages=pages,
        leaves=build_leaves(pages),
        start_page=request.args.get("page", default=0, type=int),
    )


@bp.route("/realms/<realm_slug>/<book_slug>/write", methods=["GET", "POST"])
def write(realm_slug: str, book_slug: str):
    """Add a new entry to a book. Stored in Vercel Blob (or local storage in dev)."""
    realm, book = catalog().get_book(realm_slug, book_slug)
    if not book:
        abort(404)
    passcode_required = bool(current_app.config.get("WRITE_PASSCODE"))
    form = {"title": "", "author": "", "body": "", "image_alt": "", "caption": ""}
    errors: dict[str, str] = {}

    if request.method == "POST":
        expected = session.get("csrf")
        if not expected or not hmac.compare_digest(request.form.get("csrf", ""), expected):
            abort(400, "Your form expired. Reload the page and try again.")
        form = {k: (request.form.get(k) or "").strip() for k in form}
        if passcode_required and not hmac.compare_digest(
            request.form.get("passcode", ""), current_app.config["WRITE_PASSCODE"]
        ):
            errors["passcode"] = "That passcode is not right."
        if not form["title"]:
            errors["title"] = "Give the entry a title."
        elif len(form["title"]) > MAX_TITLE:
            errors["title"] = f"Keep the title under {MAX_TITLE} characters."
        if len(form["author"]) > MAX_AUTHOR:
            errors["author"] = f"Keep the name under {MAX_AUTHOR} characters."
        if not form["body"]:
            errors["body"] = "Write the entry before publishing."
        elif len(form["body"]) > MAX_BODY:
            errors["body"] = f"Keep the entry under {MAX_BODY} characters; split longer ones into several entries."

        image = request.files.get("image")
        image_data, image_type = None, None
        if image and image.filename:
            image_data = image.read(MAX_IMAGE_BYTES + 1)
            image_type = sniff_image(image_data)
            if len(image_data) > MAX_IMAGE_BYTES:
                errors["image"] = "Images can be up to 4 MB."
            elif not image_type:
                errors["image"] = "Use a PNG, JPEG, GIF or WebP image."
            elif not form["image_alt"]:
                errors["image_alt"] = "Describe the image for readers who can't see it."

        if not errors:
            try:
                image_path = (
                    repo().save_image(realm.slug, book.slug, image_data, image_type) if image_data else None
                )
                entry = Entry(
                    realm=realm.slug,
                    book=book.slug,
                    title=form["title"],
                    author=form["author"] or "Anonymous",
                    body=form["body"],
                    published_at=datetime.now(timezone.utc),
                    image_path=image_path,
                    image_alt=form["image_alt"] if image_path else "",
                    caption=form["caption"] if image_path else "",
                )
                repo().add(entry)
            except StorageError:
                current_app.logger.exception("Could not save entry")
                errors["form"] = "The archive could not save your entry. Try again in a moment."
            else:
                # The newest entry is page index 1 (right after the contents page).
                return redirect(url_for("main.book", realm_slug=realm.slug, book_slug=book.slug, page=1))

    return render_template(
        "write.html",
        realm=realm,
        book=book,
        form=form,
        errors=errors,
        passcode_required=passcode_required,
        limits={"title": MAX_TITLE, "author": MAX_AUTHOR, "body": MAX_BODY},
    ), (422 if errors else 200)


@bp.get("/media/<path:pathname>")
def media(pathname: str):
    """Serve uploaded images from storage (works for public and private Blob stores)."""
    try:
        data, content_type = repo().read_media(pathname)
    except NotFound:
        abort(404)
    except StorageError:
        current_app.logger.exception("Could not read media")
        abort(502)
    response = Response(data, mimetype=content_type)
    response.headers["Cache-Control"] = "public, max-age=86400, immutable"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@bp.get("/healthz")
def healthz():
    return {"ok": True, "storage": repo().store.name}


@bp.app_errorhandler(404)
def not_found(_error):
    return render_template("errors/404.html"), 404
