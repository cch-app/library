# Lumen Archive

A game-like library of knowledge from every field, built with **Flask**, **Tailwind CSS v4** and **Vercel Blob**, ready to deploy on **Vercel**.

1. **The gate** (`/`): tap the door, the Gatekeeper asks *“Will you enter the realm?”* in the middle of the door opening; **Yes** opens it fully and you step into the light, **No** closes it again.
2. **The aisle of realms** (`/realms`): a first-person 3D aisle. Tap the upper aisle to walk forward and the lower aisle to step back; the green **EXIT** at the entrance plays the gate in reverse. Each bookshelf is a realm; tapping one turns you toward it and opens its bookcase of books (topics).
3. **The book** (`/realms/<realm>/<book>`): an open book with a contents page and one page per entry, **newest first**. Pages turn over the spine in 3D. On phones the whole open book stays on the desk and the view glides between its left and right pages.
4. **Write an entry** (`/realms/<realm>/<book>/write`): adds a new page (with an optional illustration) to the book. Entries and images are stored in Vercel Blob.

## Project layout

```
app.py                     Vercel entrypoint (exports `app`)
lumen/
  __init__.py              create_app(): config, storage, blueprint, CLI
  catalog.py               realms and books from data/catalog.json
  entries.py               Entry model, repository (with cache), book page/leaf layout
  storage.py               BlobStore (vercel-blob SDK) and LocalStore (dev/tests)
  routes.py                gate, aisle, book, write, media, healthz
  cli.py                   `flask seed`
  templates/               Jinja templates styled with Tailwind utilities
data/
  catalog.json             the 8 realms and their books, edit to add your own
  seed_entries.json        sample entries for "Consistent hashing"
assets/tailwind.css        Tailwind v4 source: theme tokens + 3D scene components
public/static/             served by Vercel's CDN: built css, js, images
tests/test_app.py          pytest suite (uses local storage)
vercel.json                build command (Tailwind) and function settings
```

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
npm install && npm run build:css      # or: npm run watch:css while editing templates
flask --app app run --debug
```

Without a Blob token the app stores entries as files in `./.data/` and seeds the sample entries automatically. To use your real Blob store locally, run `vercel env pull .env` first (it writes `BLOB_READ_WRITE_TOKEN`), then `flask --app app seed`.

Run the tests with `pip install pytest && pytest`.

## Deploy to Vercel

1. Push this folder to a Git repository and import it in Vercel. The Flask preset is detected from `app.py`; `vercel.json` adds the Tailwind build (`npm ci && npm run build:css`).
2. In the project, open **Storage → Create → Blob**, create a store and connect it to the project. Vercel adds `BLOB_READ_WRITE_TOKEN` to the environment.
   - If you create a **private** store, also set `BLOB_ACCESS=private`. Images are always served through `/media/…`, so both modes work.
3. In **Settings → Environment Variables**, set `SECRET_KEY` to a long random string. Optionally set `WRITE_PASSCODE` so only people with the passcode can publish.
4. Deploy, then add the sample entries once:
   ```bash
   vercel env pull .env
   flask --app app seed
   ```

### How storage is laid out in Blob

```
entries/<realm>/<book>/<YYYYmmddTHHMMSS>-<slug>-<id>.json   one entry per object
media/<realm>/<book>/<random>.png                           uploaded illustrations
```

Listings are cached for `CACHE_TTL` seconds (default 30) inside a warm function, and every write clears the cache.

## Environment variables

| Name | Default | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | `dev-only-change-me` | Signs the session cookie used for the form's CSRF token. **Set this in production.** |
| `BLOB_READ_WRITE_TOKEN` | — | Vercel Blob credentials (added when you connect a store). |
| `BLOB_ACCESS` | `public` | `public` or `private`; must match the store. |
| `STORAGE_BACKEND` | `auto` | `auto` uses Blob when credentials exist, otherwise local files. Force with `blob` or `local`. |
| `WRITE_PASSCODE` | — | If set, publishing an entry requires it. |
| `CACHE_TTL` | `30` | Seconds to cache entry listings per function instance. |

## Customising

- **Realms and books:** edit `data/catalog.json`. The aisle grows by one step for every two realms.
- **Look and feel:** colours, fonts and animations are theme tokens in `assets/tailwind.css` (`--color-gold-400`, `--font-display`, …), used as utilities like `text-gold-400` or `font-display` in the templates.
- **Long entries:** a page scrolls inside the book if an entry is longer than one page. Entries are capped at 6,000 characters.

## Notes

- Vercel Functions accept request bodies up to 4.5 MB, so uploads are limited to 4 MB.
- The page-turn and aisle scenes respect `prefers-reduced-motion`.
