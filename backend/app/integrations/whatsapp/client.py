"""
WhatsApp Cloud API integration (Phase 11).

Verified against Meta's current WhatsApp Cloud API docs:
- Send: POST https://graph.facebook.com/v23.0/<PHONE_NUMBER_ID>/messages
  with messaging_product="whatsapp", Bearer token auth.
- Webhook GET verify handshake and X-Hub-Signature-256 POST signing work
  exactly like Messenger (same Meta app infra) — signature verification
  is reused from app.integrations.facebook.client.verify_signature rather
  than duplicated.
"""
import logging

import requests

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v23.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class WhatsAppClient:
    """Thin wrapper around the WhatsApp Cloud API Messages endpoint.
    Isolated here so no other module talks to graph.facebook.com directly,
    and so it can be swapped for FakeWhatsAppClient in tests/local dev."""

    def __init__(self, access_token: str):
        if not access_token:
            raise ValueError("access_token is required")
        self._token = access_token

    def send_text_message(self, phone_number_id: str, to: str, text: str) -> None:
        """Send a plain text reply from the business's WhatsApp number.
        Raises on failure — caller (webhook route) must catch, log, and
        still ack Meta's POST with 200 so Meta doesn't endlessly retry."""
        url = f"{GRAPH_API_BASE}/{phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": text},
        }
        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10,
        )
        if resp.status_code >= 300:
            logger.error(
                "WhatsApp Cloud API error status=%s body=%s",
                resp.status_code,
                resp.text[:500],
            )
            resp.raise_for_status()


class FakeWhatsAppClient:
    """No-network stand-in for local testing (no WHATSAPP_ACCESS_TOKEN set)
    and for unit tests. Records every send so tests can assert on it."""

    def __init__(self):
        self.sent_messages = []

    def send_text_message(self, phone_number_id: str, to: str, text: str) -> None:
        self.sent_messages.append(
            {"phone_number_id": phone_number_id, "to": to, "text": text}
        )
        logger.info(
            "[FakeWhatsAppClient] would send from %s to %s: %s",
            phone_number_id,
            to,
            text,
        )
