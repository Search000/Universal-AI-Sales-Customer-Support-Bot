"""
Owner Dashboard — Conversations (Phase 12, sub-phase 1).

Read-only view for the business owner: every customer conversation state
we're currently holding for their business, so they can see who's talked
to the bot and who needs a human.

Built gradually per the master prompt (one dashboard section at a time).
This is Conversations only — Orders/Products/etc. are later sub-phases.
"""
import logging
from dataclasses import asdict

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


@dashboard_bp.get("/dashboard/orders")
def list_orders():
    business_id = request.args.get("business_id")
    if not business_id:
        return jsonify({"error": "business_id is required"}), 400

    customer_id = request.args.get("customer_id")
    status = request.args.get("status")

    repo = get_repository()
    try:
        orders = repo.list_orders(business_id, customer_id=customer_id)
    except BusinessIdRequiredError as exc:
        return jsonify({"error": str(exc)}), 400

    rows = [o.to_row() for o in orders]
    if status:
        rows = [r for r in rows if r.get("status") == status]

    # Newest first — same reasoning as Conversations: an owner opening the
    # dashboard wants to see the latest activity, not the oldest.
    rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)

    return jsonify({"orders": rows, "count": len(rows)}), 200


@dashboard_bp.get("/dashboard/products")
def list_products():
    business_id = request.args.get("business_id")
    if not business_id:
        return jsonify({"error": "business_id is required"}), 400

    active_only = request.args.get("active_only") == "true"

    repo = get_repository()
    try:
        products = repo.list_products(business_id)
    except BusinessIdRequiredError as exc:
        return jsonify({"error": str(exc)}), 400

    rows = [asdict(p) for p in products]
    if active_only:
        rows = [r for r in rows if str(r.get("active", "")).upper() == "TRUE"]

    rows.sort(key=lambda r: r.get("product_name", "").lower())

    return jsonify({"products": rows, "count": len(rows)}), 200
