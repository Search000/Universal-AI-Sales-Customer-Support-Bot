"""
Security helpers (Phase 14).

Three independent, narrowly-scoped pieces:

1. require_owner_api_key — protects owner-only endpoints (dashboard,
   learning queue review, follow-up automation, /test/message) with a
   shared-secret header. Customer-facing webhooks are NOT protected this
   way — they're authenticated by Meta's own request signature instead
   (see app.integrations.facebook.client.verify_signature).

2. sanitize_sheet_value — defends against CSV/spreadsheet formula
   injection. Anything a customer typed can end up in a Google Sheets
   cell (e.g. an unknown-term learning-queue entry). If that cell starts
   with =, +, -, or @, Excel/Sheets can interpret it as a formula when
   the owner opens the sheet (a well-known "CSV injection" attack, e.g.
   =HYPERLINK(...) or DDE payloads). We neutralize this by prefixing a
   single quote, which spreadsheet software treats as "force text" and
   Google Sheets/Excel both already display without the quote.

3. RateLimiter — a minimal in-memory fixed-window limiter for
   public-facing endpoints (webhooks, /test/message), to blunt basic
   spam/DoS given this project intentionally has no paid infrastructure
   (e.g. a WAF) in front of it. Single-process only by design — documented
   limitation for a multi-instance deployment.
"""
import logging
import threading
import time
from functools import wraps
from typing import Dict, Tuple

from flask import jsonify, request

from app.config import config

logger = logging.getLogger(__name__)

_FORMULA_PREFIXES = ("=", "+", "-", "@")


def sanitize_sheet_value(value):
    """Neutralize spreadsheet-formula-injection payloads before they are
    ever written to a real Google Sheet. Non-strings pass through
    unchanged; only leading-formula-character strings are prefixed."""
    if not isinstance(value, str):
        return value
    if value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def sanitize_row(row: dict) -> dict:
    """Applies sanitize_sheet_value to every value in a row dict."""
    return {k: sanitize_sheet_value(v) for k, v in row.items()}


def check_owner_api_key():
    """Call from a blueprint's before_request. Returns a Flask response to
    short-circuit the request if unauthorized, or None to let it proceed.

    Enforced only once OWNER_API_KEY is actually configured — mirrors the
    existing pattern for webhook signatures (never silently enforced
    against an empty secret). Until it's set, every owner-only endpoint
    stays reachable but logs a loud warning on every call, so this is
    impossible to miss during setup — not a silent gap.
    """
    if not config.OWNER_API_KEY:
        logger.warning(
            "OWNER_API_KEY is not set — owner-only endpoint %s is "
            "currently UNPROTECTED. Set OWNER_API_KEY before exposing "
            "this server to the internet.",
            request.path,
        )
        return None

    import hmac

    provided = request.headers.get("X-API-Key", "")
    if not provided or not hmac.compare_digest(provided, config.OWNER_API_KEY):
        logger.warning("Rejected owner-endpoint request to %s: bad/missing API key", request.path)
        return jsonify({"error": "unauthorized"}), 401
    return None


def require_owner_api_key(view_func):
    """Decorator form of check_owner_api_key, for a single route."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        blocked = check_owner_api_key()
        if blocked is not None:
            return blocked
        return view_func(*args, **kwargs)

    return wrapped


class RateLimiter:
    """Fixed-window limiter: at most `limit` calls per `window_seconds`
    per key (typically the caller's IP). Thread-safe, in-memory only."""

    def __init__(self, limit: int, window_seconds: int = 60):
        self._limit = limit
        self._window = window_seconds
        self._hits: Dict[str, Tuple[int, float]] = {}  # key -> (count, window_start)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            count, window_start = self._hits.get(key, (0, now))
            if now - window_start >= self._window:
                count, window_start = 0, now
            count += 1
            self._hits[key] = (count, window_start)
            return count <= self._limit


_webhook_limiter = RateLimiter(limit=max(config.RATE_LIMIT_PER_MINUTE, 1), window_seconds=60)


def check_rate_limit():
    """Call from a blueprint's before_request. Returns a 429 response if
    the caller (by IP) has exceeded RATE_LIMIT_PER_MINUTE, else None."""
    key = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")
    if not _webhook_limiter.allow(key):
        logger.warning("Rate limit exceeded for %s on %s", key, request.path)
        return jsonify({"error": "rate limit exceeded"}), 429
    return None


def rate_limited(view_func):
    """Decorator form of check_rate_limit, for a single route."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        blocked = check_rate_limit()
        if blocked is not None:
            return blocked
        return view_func(*args, **kwargs)

    return wrapped
