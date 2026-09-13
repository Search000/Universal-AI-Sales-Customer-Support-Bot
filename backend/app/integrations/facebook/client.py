"""
Facebook Messenger integration (Phase 10).

Two responsibilities, kept separate from the webhook route so they're
independently testable:
1. verify_signature() — proves a POST body genuinely came from Meta
   (HMAC-SHA256 over the RAW body, keyed with the app secret).
2. FacebookClient — sends replies back to the customer via the Send API.

Verified against Meta's current Messenger Platform webhook docs (GET
verify handshake echoes hub.challenge; POST bodies are signed with
X-Hub-Signature-256 = "sha256=<hex hmac of raw body>").
"""
import hashlib
import hmac
import logging

import requests

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def verify_signature(app_secret: str, raw_body: bytes, signature_header: str) -> bool:
    """Validate X-Hub-Signature-256 against the RAW request body.

    Must run before any JSON parsing/re-serialization — Meta signs the
    exact bytes it sent, and a re-encoded copy will not match.
    """
    if not app_secret or not signature_header:
        return False
    if not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        app_secret.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    provided = signature_header.split("sha256=", 1)[1].strip()
    return hmac.compare_digest(expected, provided)


class FacebookClient:
    """Thin wrapper around the Messenger Send API. Isolated here so no
    other module talks to graph.facebook.com directly, and so it can be
    swapped for FakeFacebookClient in tests / local dev without a token."""

    def __init__(self, page_access_token: str):
        if not page_access_token:
            raise ValueError("page_access_token is required")
        self._token = page_access_token

    def send_text_message(self, recipient_id: str, text: str) -> None:
        """Send a plain text reply. Raises on failure — the caller (webhook
        route) must catch, log, and still ack Meta's POST with 200 so
        Meta does not endlessly retry delivery of the inbound event."""
        url = f"{GRAPH_API_BASE}/me/messages"
        payload = {
            "recipient": {"id": recipient_id},
            "messaging_type": "RESPONSE",
            "message": {"text": text},
        }
        resp = requests.post(
            url,
            params={"access_token": self._token},
            json=payload,
            timeout=10,
        )
        if resp.status_code >= 300:
            logger.error(
                "Facebook Send API error status=%s body=%s",
                resp.status_code,
                resp.text[:500],
            )
            resp.raise_for_status()


class FakeFacebookClient:
    """No-network stand-in for local testing (no META_PAGE_ACCESS_TOKEN
    set) and for unit tests. Records every send so tests can assert on it."""

    def __init__(self):
        self.sent_messages = []

    def send_text_message(self, recipient_id: str, text: str) -> None:
        self.sent_messages.append({"recipient_id": recipient_id, "text": text})
        logger.info("[FakeFacebookClient] would send to %s: %s", recipient_id, text)
