"""
Local "production-style" entrypoint (Phase 4 of hosting, PC-first stage).

`python main.py` runs Flask's own dev server — fine for testing, but it is
single-threaded, reloads on file changes, and logs a warning that it is
not meant to serve real traffic. This script runs the exact same app
through waitress, a production-grade WSGI server that (unlike gunicorn)
works on Windows, so this PC can host the bot properly until it moves to
a paid server later.

Usage:
    python run_production.py

Reads APP_PORT from the same .env / Config the rest of the app uses, so
no separate configuration is needed.
"""
import logging

from waitress import serve

from app import create_app
from app.config import config

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = create_app()

if __name__ == "__main__":
    if not config.OWNER_API_KEY:
        logger.warning(
            "OWNER_API_KEY is not set in .env — dashboard/learning/follow-up "
            "endpoints are currently UNPROTECTED. Set it before this server "
            "is reachable from outside your own PC."
        )
    logger.info("Starting production-style server on 0.0.0.0:%s (waitress)", config.APP_PORT)
    serve(app, host="0.0.0.0", port=config.APP_PORT, threads=8)
