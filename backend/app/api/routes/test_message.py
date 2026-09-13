import logging

from flask import Blueprint, jsonify, request

from app.integrations.sheets.repository import BusinessIdRequiredError
from app.services.engine_factory import get_message_pipeline
from app.services.security import check_owner_api_key, check_rate_limit

logger = logging.getLogger(__name__)

test_message_bp = Blueprint("test_message", __name__)


@test_message_bp.before_request
def _enforce_auth_and_rate_limit():
    """/test/message is a developer/owner tool, not a real customer
    channel (Facebook/WhatsApp webhooks are) — so it gets the same
    owner-only protection as the dashboard, plus a rate limit since it
    can trigger real Gemini/Sheets calls per request."""
    blocked = check_owner_api_key()
    if blocked is not None:
        return blocked
    return check_rate_limit()


@test_message_bp.post("/test/message")
def handle_test_message():
    data = request.get_json(silent=True) or {}
    business_id = data.get("business_id")
    customer_id = data.get("customer_id", "test_customer")
    message = data.get("message")

    if not business_id or not message:
        return jsonify({"error": "business_id and message are required"}), 400

    pipeline = get_message_pipeline()
    try:
        result = pipeline.handle_message(business_id, customer_id, message)
    except BusinessIdRequiredError as exc:
        return jsonify({"error": str(exc)}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        logger.exception("Unexpected error handling /test/message")
        return jsonify({"error": "internal error"}), 500

    return jsonify(result), 200
