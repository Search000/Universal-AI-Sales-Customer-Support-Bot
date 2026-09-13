"""
Owner Dashboard — Conversations (Phase 12, sub-phase 1).

Read-only view for the business owner: every customer conversation state
we're currently holding for their business, so they can see who's talked
to the bot and who needs a human.

Built gradually per the master prompt (one dashboard section at a time).
This is Conversations only — Orders/Products/etc. are later sub-phases.
"""
import logging

from flask import Blueprint, jsonify, request

from app.integrations.sheets.repository import BusinessIdRequiredError
from app.services.engine_factory import get_repository

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/dashboard/conversations")
def list_conversations():
    business_id = request.args.get("business_id")
    if not business_id:
        return jsonify({"error": "business_id is required"}), 400

    needs_human_only = request.args.get("needs_human") == "true"

    repo = get_repository()
    try:
        conversations = repo.list_conversation_memories(business_id)
    except BusinessIdRequiredError as exc:
        return jsonify({"error": str(exc)}), 400

    rows = [c.to_row() for c in conversations]
    if needs_human_only:
        rows = [r for r in rows if str(r.get("human_required", "")).upper() == "TRUE"]

    # Most recently updated first — that's what an owner opening the
    # dashboard actually wants to see.
    rows.sort(key=lambda r: r.get("updated_at", ""), reverse=True)

    return jsonify({"conversations": rows, "count": len(rows)}), 200
