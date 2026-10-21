import io
import re

import pytest

from lumen import create_app
from lumen.catalog import slugify
from lumen.entries import build_leaves, build_pages


@pytest.fixture()
def app(tmp_path):
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "test",
        "STORAGE_BACKEND": "local",
        "LOCAL_STORAGE_DIR": str(tmp_path / "store"),
    })


@pytest.fixture()
def client(app):
    return app.test_client()


def csrf(client, url):
    html = client.get(url).get_data(as_text=True)
    return re.search(r'name="csrf" value="([^"]+)"', html).group(1)


def test_slugify():
    assert slugify("Bayes' theorem") == "bayes-theorem"
    assert slugify("Gödel's theorems") == "godel-s-theorems"
    assert slugify("TCP/IP") == "tcp-ip"


def test_gate_and_return(client):
    assert b"GATEKEEPER" in client.get("/").data
    assert b'data-phase="away"' in client.get("/?from=library").data


def test_aisle_lists_every_realm(client):
    html = client.get("/realms").get_data(as_text=True)
    for name in ["Computing", "Mathematics", "Physics", "Life Sciences", "History", "Philosophy", "Economics", "Arts &amp; Letters"]:
        assert name in html
    assert "Dawn over the Still Lake" in html


def test_aisle_opens_shelf_and_highlights_book(client):
    html = client.get("/realms?shelf=computing&book=consistent-hashing").get_data(as_text=True)
    assert 'data-open="computing"' in html
    assert "is-last" in html


def test_book_shows_seeded_entries_newest_first(client):
    html = client.get("/realms/computing/consistent-hashing").get_data(as_text=True)
    newest = html.index("Virtual nodes in practice")
    oldest = html.index("Why hash mod N breaks")
    assert newest < oldest
    assert 'data-pages="7"' in html


def test_empty_book_and_unknown_book(client):
    assert b"This book is still blank." in client.get("/realms/physics/optics").data
    assert client.get("/realms/physics/not-a-book").status_code == 404


def test_write_entry_with_image(client):
    url = "/realms/physics/optics/write"
    token = csrf(client, url)
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    resp = client.post(url, data={
        "csrf": token, "title": "Why the sky is blue", "author": "Ada",
        "body": "Rayleigh scattering.\n\nShort wavelengths scatter more.",
        "image": (io.BytesIO(png), "sky.png"), "image_alt": "Diagram of scattering", "caption": "",
    }, content_type="multipart/form-data")
    assert resp.status_code == 302 and resp.headers["Location"].endswith("page=1")

    html = client.get("/realms/physics/optics").get_data(as_text=True)
    assert "Why the sky is blue" in html and "by Ada" in html
    media = re.search(r'src="(/media/[^"]+)"', html).group(1)
    image = client.get(media)
    assert image.status_code == 200 and image.mimetype == "image/png"


def test_write_validation_and_csrf(client):
    url = "/realms/physics/optics/write"
    assert client.post(url, data={"title": "x", "body": "y"}).status_code == 400
    token = csrf(client, url)
    resp = client.post(url, data={"csrf": token, "title": "", "body": ""})
    assert resp.status_code == 422
    assert b"Give the entry a title." in resp.data


def test_write_passcode(tmp_path):
    app = create_app({"TESTING": True, "STORAGE_BACKEND": "local", "LOCAL_STORAGE_DIR": str(tmp_path), "WRITE_PASSCODE": "open-sesame"})
    client = app.test_client()
    url = "/realms/history/silk-road/write"
    resp = client.post(url, data={"csrf": csrf(client, url), "title": "T", "body": "B", "passcode": "nope"})
    assert resp.status_code == 422
    resp = client.post(url, data={"csrf": csrf(client, url), "title": "T", "body": "B", "passcode": "open-sesame"})
    assert resp.status_code == 302


def test_media_rejects_paths_outside_media(client):
    assert client.get("/media/entries/computing/consistent-hashing/x.json").status_code == 404
    assert client.get("/media/../secret").status_code == 404


@pytest.mark.parametrize("entries,leaves", [(0, 1), (1, 1), (5, 3), (6, 4)])
def test_leaf_layout(entries, leaves):
    pages = build_pages([None] * entries)  # entries are only counted here
    assert len(build_leaves(pages)) == leaves
