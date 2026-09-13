from app import create_app


def test_dashboard_faq_missing_business_id():
    app = create_app()
    client = app.test_client()
    resp = client.get("/dashboard/faq")
    assert resp.status_code == 400


def test_dashboard_faq_lists_faqs_for_business():
    app = create_app()
    client = app.test_client()

    resp = client.get("/dashboard/faq", query_string={"business_id": "biz_001"})
    assert resp.status_code == 200
    body = resp.get_json()
    questions = {f["question"] for f in body["faqs"]}
    assert "Delivery koto din lage?" in questions
    assert body["count"] == 1


def test_dashboard_faq_business_isolation():
    app = create_app()
    client = app.test_client()

    resp = client.get("/dashboard/faq", query_string={"business_id": "biz_002"})
    body = resp.get_json()
    questions = {f["question"] for f in body["faqs"]}
    assert "Delivery koto din lage?" not in questions


def test_dashboard_faq_active_only_filter():
    app = create_app()
    client = app.test_client()

    resp = client.get(
        "/dashboard/faq",
        query_string={"business_id": "biz_001", "active_only": "true"},
    )
    assert resp.status_code == 200
    for faq in resp.get_json()["faqs"]:
        assert faq["active"].upper() == "TRUE"
