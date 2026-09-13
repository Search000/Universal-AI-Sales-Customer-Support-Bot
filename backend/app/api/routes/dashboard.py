"""
Owner Dashboard — Conversations (Phase 12, sub-phase 1).

Read-only view for the business owner: every customer conversation state
we're currently holding for their business, so they can see who's talked
to the bot and who needs a human.

Built gradually per the master prompt (one dashboard section at a time).
This is Conversations only — Orders/Products/etc. are later sub-phases.
"""
import logging
import secrets
from dataclasses import asdict
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.integrations.sheets.repository import BusinessIdRequiredError
from app.models.business import Business
from app.services.engine_factory import get_repository
from app.services.security import check_owner_api_key

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.before_request
def _enforce_owner_auth():
    """Every /dashboard/* route is owner-only (Phase 14) — see
    app.services.security.check_owner_api_key for the enforcement rule."""
    return check_owner_api_key()


@dashboard_bp.post("/dashboard/businesses")
def create_business():
    """One-click client onboarding: give it a business name/type/contact
    info, it generates a unique business_id and writes the new row to the
    BUSINESSES sheet. This is the ONLY route allowed to create a business —
    everything else in the app only ever reads or updates an existing one."""
    data = request.get_json(silent=True) or {}

    business_name = (data.get("business_name") or "").strip()
    business_type = (data.get("business_type") or "").strip()
    if not business_name or not business_type:
        return jsonify({"error": "business_name and business_type are required"}), 400

    repo = get_repository()

    # Astronomically unlikely to collide, but retry a few times rather than
    # trust that blindly.
    business_id = None
    for _ in range(5):
        candidate = "biz_" + secrets.token_hex(4)
        if repo.get_business(candidate) is None:
            business_id = candidate
            break
    if business_id is None:
        return jsonify({"error": "could not generate a unique business_id, try again"}), 500

    business = Business(
        business_id=business_id,
        business_name=business_name,
        business_type=business_type,
        facebook_page_id=data.get("facebook_page_id", ""),
        whatsapp_phone_number_id=data.get("whatsapp_phone_number_id", ""),
        phone=data.get("phone", ""),
        email=data.get("email", ""),
        address=data.get("address", ""),
        opening_hours=data.get("opening_hours", ""),
        currency=data.get("currency", "BDT"),
        default_language=data.get("default_language", "bn"),
        status="active",
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    try:
        repo.create_business(business)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 409

    return jsonify({"status": "created", "business": asdict(business)}), 201


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


@dashboard_bp.get("/dashboard/services")
def list_services():
    business_id = request.args.get("business_id")
    if not business_id:
        return jsonify({"error": "business_id is required"}), 400

    active_only = request.args.get("active_only") == "true"

    repo = get_repository()
    try:
        services = repo.list_services(business_id)
    except BusinessIdRequiredError as exc:
        return jsonify({"error": str(exc)}), 400

    rows = [asdict(s) for s in services]
    if active_only:
        rows = [r for r in rows if str(r.get("active", "")).upper() == "TRUE"]

    rows.sort(key=lambda r: r.get("service_name", "").lower())

    return jsonify({"services": rows, "count": len(rows)}), 200


@dashboard_bp.get("/dashboard/faq")
def list_faq():
    business_id = request.args.get("business_id")
    if not business_id:
        return jsonify({"error": "business_id is required"}), 400

    active_only = request.args.get("active_only") == "true"

    repo = get_repository()
    try:
        faqs = repo.list_faqs(business_id)
    except BusinessIdRequiredError as exc:
        return jsonify({"error": str(exc)}), 400

    rows = [asdict(f) for f in faqs]
    if active_only:
        rows = [r for r in rows if str(r.get("active", "")).upper() == "TRUE"]

    rows.sort(key=lambda r: r.get("question", "").lower())

    return jsonify({"faqs": rows, "count": len(rows)}), 200


@dashboard_bp.get("/dashboard/policies")
def list_policies():
    business_id = request.args.get("business_id")
    if not business_id:
        return jsonify({"error": "business_id is required"}), 400

    active_only = request.args.get("active_only") == "true"

    repo = get_repository()
    try:
        policies = repo.list_policies(business_id)
    except BusinessIdRequiredError as exc:
        return jsonify({"error": str(exc)}), 400

    rows = [asdict(p) for p in policies]
    if active_only:
        rows = [r for r in rows if str(r.get("active", "")).upper() == "TRUE"]

    rows.sort(key=lambda r: r.get("policy_type", "").lower())

    return jsonify({"policies": rows, "count": len(rows)}), 200


@dashboard_bp.get("/dashboard/vocabulary")
def list_vocabulary():
    business_id = request.args.get("business_id")
    if not business_id:
        return jsonify({"error": "business_id is required"}), 400

    # Owner dashboard shows everything by default (approved AND any
    # manually-added unapproved terms) — pass approved_only=true to filter
    # down to just the trusted, in-use vocabulary.
    approved_only = request.args.get("approved_only") == "true"

    repo = get_repository()
    try:
        vocab = repo.list_vocabulary(business_id, approved_only=approved_only)
    except BusinessIdRequiredError as exc:
        return jsonify({"error": str(exc)}), 400

    rows = [v.to_row() for v in vocab]
    rows.sort(key=lambda r: r.get("term", "").lower())

    return jsonify({"vocabulary": rows, "count": len(rows)}), 200


# Fields an owner is allowed to change via the dashboard. business_id and
# created_at are identity fields — never editable through this endpoint.
_EDITABLE_BUSINESS_FIELDS = {
    "business_name",
    "business_type",
    "facebook_page_id",
    "whatsapp_phone_number_id",
    "phone",
    "email",
    "address",
    "opening_hours",
    "currency",
    "default_language",
    "status",
}


@dashboard_bp.get("/dashboard/settings")
def get_settings():
    business_id = request.args.get("business_id")
    if not business_id:
        return jsonify({"error": "business_id is required"}), 400

    repo = get_repository()
    try:
        business = repo.get_business(business_id)
    except BusinessIdRequiredError as exc:
        return jsonify({"error": str(exc)}), 400

    if business is None:
        return jsonify({"error": "business not found"}), 404

    return jsonify({"settings": asdict(business)}), 200


@dashboard_bp.post("/dashboard/settings")
def update_settings():
    data = request.get_json(silent=True) or {}
    business_id = data.get("business_id")
    if not business_id:
        return jsonify({"error": "business_id is required"}), 400

    repo = get_repository()
    try:
        business = repo.get_business(business_id)
    except BusinessIdRequiredError as exc:
        return jsonify({"error": str(exc)}), 400

    if business is None:
        return jsonify({"error": "business not found"}), 404

    # Partial update: only touch fields the owner actually sent, and only
    # ones on the allowed list — business_id/created_at can never change
    # through this endpoint no matter what the request body contains.
    updated_fields = []
    for field, value in data.items():
        if field in _EDITABLE_BUSINESS_FIELDS:
            setattr(business, field, value)
            updated_fields.append(field)

    repo.update_business(business)

    return jsonify({"status": "updated", "updated_fields": updated_fields, "settings": asdict(business)}), 200


@dashboard_bp.get("/dashboard/analytics")
def get_analytics():
    """Simple counts/totals an owner cares about at a glance. Deliberately
    basic for this sub-phase — no time-windowing or charts yet, just
    trustworthy numbers pulled straight from verified business data."""
    business_id = request.args.get("business_id")
    if not business_id:
        return jsonify({"error": "business_id is required"}), 400

    repo = get_repository()
    try:
        conversations = repo.list_conversation_memories(business_id)
        orders = repo.list_orders(business_id)
        products = repo.list_products(business_id)
        services = repo.list_services(business_id)
        pending_learning = repo.list_learning_queue(business_id, status="pending")
    except BusinessIdRequiredError as exc:
        return jsonify({"error": str(exc)}), 400

    orders_by_status = {}
    total_revenue = 0.0
    for order in orders:
        orders_by_status[order.status] = orders_by_status.get(order.status, 0) + 1
        try:
            total_revenue += float(order.total_price)
        except (ValueError, TypeError):
            # Never let one malformed row crash the whole analytics call —
            # just skip it from the revenue sum.
            pass

    conversations_needing_human = sum(
        1 for c in conversations if str(c.human_required).upper() == "TRUE"
    )

    return jsonify(
        {
            "business_id": business_id,
            "total_conversations": len(conversations),
            "conversations_needing_human": conversations_needing_human,
            "total_orders": len(orders),
            "orders_by_status": orders_by_status,
            "total_revenue": total_revenue,
            "total_products": len(products),
            "total_services": len(services),
            "pending_learning_queue": len(pending_learning),
        }
    ), 200
