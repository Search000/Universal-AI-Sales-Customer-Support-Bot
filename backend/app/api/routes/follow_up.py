"""
Follow-Up / Sales Automation API (Phase 13).

Read-only endpoints the owner dashboard (or a scheduled job) can call to
find abandoned conversations/orders, get product recommendations and
upsell suggestions, and see customer segments. Every response is scoped
to a single business_id, same isolation rule as every other route.
"""
import logging
from dataclasses import asdict

from flask import Blueprint, jsonify, request

from app.integrations.sheets.repository import BusinessIdRequiredError
from app.services.engine_factory import get_follow_up_engine

logger = logging.getLogger(__name__)

follow_up_bp = Blueprint("follow_up", __name__)


def _require_business_id():
    business_id = request.args.get("business_id")
    if not business_id:
        return None, (jsonify({"error": "business_id is required"}), 400)
    return business_id, None


@follow_up_bp.get("/follow-up/config")
def get_config():
    business_id, err = _require_business_id()
    if err:
        return err
    engine = get_follow_up_engine()
    return jsonify({"business_id": business_id, "config": engine.get_config(business_id)}), 200


@follow_up_bp.get("/follow-up/abandoned-conversations")
def abandoned_conversations():
    business_id, err = _require_business_id()
    if err:
        return err
    engine = get_follow_up_engine()
    try:
        results = engine.detect_abandoned_conversations(business_id)
    except BusinessIdRequiredError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"abandoned_conversations": [asdict(r) for r in results], "count": len(results)}), 200


@follow_up_bp.get("/follow-up/abandoned-orders")
def abandoned_orders():
    business_id, err = _require_business_id()
    if err:
        return err
    engine = get_follow_up_engine()
    try:
        results = engine.detect_abandoned_orders(business_id)
    except BusinessIdRequiredError as exc:
        return jsonify({"error": str(exc)}), 400
    payload = [
        {"order": r.order.to_row(), "hours_since_created": r.hours_since_created} for r in results
    ]
    return jsonify({"abandoned_orders": payload, "count": len(payload)}), 200


@follow_up_bp.get("/follow-up/message")
def follow_up_message():
    business_id, err = _require_business_id()
    if err:
        return err
    customer_id = request.args.get("customer_id")
    if not customer_id:
        return jsonify({"error": "customer_id is required"}), 400

    engine = get_follow_up_engine()
    message = engine.build_follow_up_message(business_id, customer_id)
    if message is None:
        return jsonify({"enabled": False, "message": None}), 200
    return jsonify({"enabled": True, "message": message}), 200


@follow_up_bp.get("/follow-up/recommendations")
def recommendations():
    business_id, err = _require_business_id()
    if err:
        return err
    customer_id = request.args.get("customer_id")
    if not customer_id:
        return jsonify({"error": "customer_id is required"}), 400

    engine = get_follow_up_engine()
    try:
        products = engine.recommend_products(business_id, customer_id)
    except BusinessIdRequiredError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"recommendations": [p.__dict__ for p in products], "count": len(products)}), 200


@follow_up_bp.get("/follow-up/upsell")
def upsell():
    business_id, err = _require_business_id()
    if err:
        return err
    product_id = request.args.get("product_id")
    if not product_id:
        return jsonify({"error": "product_id is required"}), 400

    engine = get_follow_up_engine()
    try:
        products = engine.suggest_upsell(business_id, product_id)
    except BusinessIdRequiredError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"upsell": [p.__dict__ for p in products], "count": len(products)}), 200


@follow_up_bp.get("/follow-up/segments")
def segments():
    business_id, err = _require_business_id()
    if err:
        return err
    engine = get_follow_up_engine()
    try:
        results = engine.segment_customers(business_id)
    except BusinessIdRequiredError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"segments": [asdict(r) for r in results], "count": len(results)}), 200
