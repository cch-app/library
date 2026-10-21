"""Vercel entrypoint: Vercel looks for a Flask instance named `app` in app.py."""

from lumen import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
