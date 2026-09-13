"""
Facebook Messenger webhook (Phase 10).

GET  /webhooks/facebook  — Meta's one-time verify handshake.
POST /webhooks/facebook  — incoming message events.

Business isolation: the Page ID in the event tells us WHICH business this
is (via SheetsRepository.get_business_by_facebook_page_id). If no business
matches that Page ID, the event is logged and dropped — we never guess.
"""
import logging

from flask import Blueprint, jsonify, request

import hmac

from app.config import config
from app.integrations.facebook.client import verify_signature
from app.services.engine_factory import (
    get_facebook_client,
    get_message_pipeline,
    get_repository,
)
from app.services.security import check_rate_limit

logger = logging.getLogger(__name__)

facebook_bp = Blueprint("facebook", __name__)


@facebook_bp.get("/webhooks/facebook")
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
        logger.info("Facebook webhook verified")
        return challenge, 200

    logger.warning("Facebook webhook verification failed (mode=%s)", mode)
    return "verification failed", 403


@facebook_bp.post("/webhooks/facebook")
def receive_webhook():
    limited = check_rate_limit()
    if limited is not None:
        return limited

    raw_body = request.get_data()

    if config.META_APP_SECRET:
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not verify_signature(config.META_APP_SECRET, raw_body, signature):
            logger.warning("Facebook webhook signature verification failed")
            return jsonify({"error": "invalid signature"}), 403
    elif config.is_production():
        # Never accept unsigned webhook traffic in production — that would
        # let anyone POST fake "customer messages" that trigger real
        # Gemini calls, Sheets writes, and outbound replies.
        logger.critical(
            "META_APP_SECRET is not set while APP_ENV=production — "
            "refusing all Facebook webhook events until it is configured."
        )
        return jsonify({"error": "webhook not configured"}), 503

    data = request.get_json(silent=True) or {}
    repo = get_repository()
    pipeline = get_message_pipeline()
    fb_client = get_facebook_client()

    for entry in data.get("entry", []):
        page_id = entry.get("id", "")
        business = repo.get_business_by_facebook_page_id(page_id)
        if business is None:
            logger.warning(
                "No business configured for Facebook page_id=%s — dropping event",
                page_id,
            )
            continue

        for event in entry.get("messaging", []):
            _handle_messaging_event(business.business_id, event, pipeline, fb_client)

    # Always ack quickly with 200 — Meta retries aggressively on non-200s,
    # and per-event errors are already logged above/below rather than
    # surfaced here.
    return jsonify({"status": "EVENT_RECEIVED"}), 200


def _handle_messaging_event(business_id: str, event: dict, pipeline, fb_client) -> None:
    sender_id = (event.get("sender") or {}).get("id")
    message = event.get("message") or {}
    text = message.get("text")

    if not sender_id or not text:
        # Non-text events (attachments, postbacks, read receipts, etc.)
        # aren't handled yet — log and skip rather than guess.
        logger.info("Skipping non-text/unsupported Facebook event: %s", event)
        return

    try:
        result = pipeline.handle_message(business_id, sender_id, text)
    except Exception:
        logger.exception(
            "Error running message pipeline for business_id=%s", business_id
        )
        return

    reply_text = result.get("response", "")
    if not reply_text:
        return

    try:
        fb_client.send_text_message(sender_id, reply_text)
    except Exception:
        logger.exception("Error sending Facebook reply to %s", sender_id)
