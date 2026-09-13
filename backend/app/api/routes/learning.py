"""
Owner-facing Learning Queue endpoints (Phase 8).

These are the ONLY endpoints allowed to create trusted VOCABULARY entries
(via approve). No customer-facing route ever calls approve() directly —
that would defeat the whole point of the queue (master rule #7).
"""
import logging

from flask import Blueprint, jsonify, request

from app.integrations.sheets.repository import BusinessIdRequiredError
from app.services.engine_factory import get_learning_engine
from app.services.learning_engine import LearningEngineError

logger = logging.getLogger(__name__)

learning_bp = Blueprint("learning", __name__)


@learning_bp.get("/learning")
def list_learning_queue():
    business_id = request.args.get("business_id")
    if not business_id:
        return jsonify({"error": "business_id is required"}), 400

    engine = get_learning_engine()
    try:
        entries = engine.list_pending(business_id)
    except BusinessIdRequiredError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"pending": [e.to_row() for e in entries]}), 200


@learning_bp.post("/learning/<learning_id>/approve")
def approve_learning_entry(learning_id: str):
    data = request.get_json(silent=True) or {}
    business_id = data.get("business_id")
    meaning = data.get("meaning")
    category = data.get("category", "")
    approved_by = data.get("approved_by", "owner")

    if not business_id or not meaning:
        return jsonify({"error": "business_id and meaning are required"}), 400

    engine = get_learning_engine()
    try:
        vocab = engine.approve(business_id, learning_id, meaning, category, approved_by)
    except LearningEngineError as exc:
        return jsonify({"error": str(exc)}), 400
    except BusinessIdRequiredError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"status": "approved", "vocabulary": vocab.to_row()}), 200


@learning_bp.post("/learning/<learning_id>/reject")
def reject_learning_entry(learning_id: str):
    data = request.get_json(silent=True) or {}
    business_id = data.get("business_id")
    reviewed_by = data.get("reviewed_by", "owner")

    if not business_id:
        return jsonify({"error": "business_id is required"}), 400

    engine = get_learning_engine()
    try:
        entry = engine.reject(business_id, learning_id, reviewed_by)
    except LearningEngineError as exc:
        return jsonify({"error": str(exc)}), 400
    except BusinessIdRequiredError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"status": "rejected", "entry": entry.to_row()}), 200
