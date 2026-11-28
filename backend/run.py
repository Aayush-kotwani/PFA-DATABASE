"""Local development server entry point."""

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    env_name = os.getenv("FLASK_ENV", "development").strip().lower()
    raw_debug = os.getenv("FLASK_DEBUG", "false").strip().lower()
    debug = False if env_name == "production" else raw_debug in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=5000, debug=debug)