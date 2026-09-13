"""
WhatsApp Cloud API webhook (Phase 11).

GET  /webhooks/whatsapp  — Meta's one-time verify handshake (same
                            hub.mode/hub.verify_token/hub.challenge scheme
                            as Messenger; same App Dashboard verify token).
POST /webhooks/whatsapp  — incoming message events.

Business isolation: the destination phone_number_id in the event tells us
WHICH business this is (via
SheetsRepository.get_business_by_whatsapp_phone_number_id). If no business
matches, the event is logged and dropped — we never guess.
"""
import logging

from flask import Blueprint, jsonify, request

import hmac

from app.config import config
from app.integrations.facebook.client import verify_signature
from app.services.engine_factory import (
    get_message_pipeline,
    get_repository,
    get_whatsapp_client,
)
from app.services.security import check_rate_limit

logger = logging.getLogger(__name__)

whatsapp_bp = Blueprint("whatsapp", __name__)


@whatsapp_bp.get("/webhooks/whatsapp")
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge", "")

    if (
        mode == "subscribe"
        and token
        and config.META_VERIFY_TOKEN
        and hmac.compare_digest(token, config.META_VERIFY_TOKEN)
    ):
        logger.info("WhatsApp webhook verified")
        return challenge, 200

    logger.warning("WhatsApp webhook verification failed (mode=%s)", mode)
    return "verification failed", 403


@whatsapp_bp.post("/webhooks/whatsapp")
def receive_webhook():
    limited = check_rate_limit()
    if limited is not None:
        return limited

    raw_body = request.get_data()

    # Same app-secret signature scheme as Messenger. Only enforced once a
    # secret is actually configured — lets local dev/testing POST without
    # a real Meta signature.
    if config.META_APP_SECRET:
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not verify_signature(config.META_APP_SECRET, raw_body, signature):
            logger.warning("WhatsApp webhook signature verification failed")
            return jsonify({"error": "invalid signature"}), 403
    elif config.is_production():
        logger.critical(
            "META_APP_SECRET is not set while APP_ENV=production — "
            "refusing all WhatsApp webhook events until it is configured."
        )
        return jsonify({"error": "webhook not configured"}), 503

    data = request.get_json(silent=True) or {}
    repo = get_repository()
    pipeline = get_message_pipeline()
    wa_client = get_whatsapp_client()

    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {}) or {}
            phone_number_id = (value.get("metadata") or {}).get("phone_number_id", "")
            business = repo.get_business_by_whatsapp_phone_number_id(phone_number_id)
            if business is None:
                logger.warning(
                    "No business configured for WhatsApp phone_number_id=%s — dropping event",
                    phone_number_id,
                )
                continue

            for message in value.get("messages", []) or []:
                _handle_message_event(
                    business.business_id, phone_number_id, message, pipeline, wa_client
                )

    # Always ack quickly with 200 — Meta retries aggressively on non-200s.
    return jsonify({"status": "EVENT_RECEIVED"}), 200


def _handle_message_event(
    business_id: str, phone_number_id: str, message: dict, pipeline, wa_client
) -> None:
    sender = message.get("from")
    text = (message.get("text") or {}).get("body")

    if not sender or not text:
        # Non-text events (images, buttons, statuses, etc.) aren't handled
        # yet — log and skip rather than guess.
        logger.info("Skipping non-text/unsupported WhatsApp event: %s", message)
        return

    try:
        result = pipeline.handle_message(business_id, sender, text)
    except Exception:
        logger.exception(
            "Error running message pipeline for business_id=%s", business_id
        )
        return

    reply_text = result.get("response", "")
    if not reply_text:
        return

    try:
        wa_client.send_text_message(phone_number_id, sender, reply_text)
    except Exception:
        logger.exception("Error sending WhatsApp reply to %s", sender)
