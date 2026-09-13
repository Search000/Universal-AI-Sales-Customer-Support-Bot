from app import create_app
from app.models.vocabulary import Vocabulary
from app.services.engine_factory import get_repository


def test_dashboard_vocabulary_missing_business_id():
    app = create_app()
    client = app.test_client()
    resp = client.get("/dashboard/vocabulary")
    assert resp.status_code == 400


def test_dashboard_vocabulary_lists_terms_for_business():
    app = create_app()
    client = app.test_client()

    resp = client.get("/dashboard/vocabulary", query_string={"business_id": "biz_001"})
    assert resp.status_code == 200
    body = resp.get_json()
    terms = {v["term"] for v in body["vocabulary"]}
    assert "boxy" in terms


def test_dashboard_vocabulary_business_isolation():
    app = create_app()
    client = app.test_client()

    resp = client.get("/dashboard/vocabulary", query_string={"business_id": "biz_001"})
    body = resp.get_json()
    terms = {v["term"] for v in body["vocabulary"]}
    # "fade" belongs to biz_002 (salon) — must never leak into biz_001.
    assert "fade" not in terms


def test_dashboard_vocabulary_approved_only_filter():
    app = create_app()
    client = app.test_client()

    # Seed an unapproved term directly (simulates a pending manual add).
    repo = get_repository()
    repo.save_vocabulary(
        Vocabulary(
            vocab_id="vocab_test_pending",
            business_id="biz_001",
            term="drop shoulder",
            meaning="loose oversized shoulder cut",
            category="clothing_style",
            examples="",
            approved="FALSE",
            updated_at="2026-01-01",
        )
    )

    resp_all = client.get("/dashboard/vocabulary", query_string={"business_id": "biz_001"})
    terms_all = {v["term"] for v in resp_all.get_json()["vocabulary"]}
    assert "drop shoulder" in terms_all

    resp_approved = client.get(
        "/dashboard/vocabulary",
        query_string={"business_id": "biz_001", "approved_only": "true"},
    )
    terms_approved = {v["term"] for v in resp_approved.get_json()["vocabulary"]}
    assert "drop shoulder" not in terms_approved
    assert "boxy" in terms_approved
