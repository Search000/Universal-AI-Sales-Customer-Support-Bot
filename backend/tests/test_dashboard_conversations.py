from app import create_app


def _send(client, business_id, customer_id, message):
    return client.post(
        "/test/message",
        json={"business_id": business_id, "customer_id": customer_id, "message": message},
    )


def test_dashboard_conversations_missing_business_id():
    app = create_app()
    client = app.test_client()
    resp = client.get("/dashboard/conversations")
    assert resp.status_code == 400


def test_dashboard_conversations_lists_customers_for_business():
    app = create_app()
    client = app.test_client()

    _send(client, "biz_001", "dash_customer_1", "black shirt XL আছে?")
    _send(client, "biz_001", "dash_customer_2", "price koto?")

    resp = client.get("/dashboard/conversations", query_string={"business_id": "biz_001"})
    assert resp.status_code == 200
    body = resp.get_json()
    customer_ids = {c["customer_id"] for c in body["conversations"]}
    assert "dash_customer_1" in customer_ids
    assert "dash_customer_2" in customer_ids


def test_dashboard_conversations_business_isolation():
    app = create_app()
    client = app.test_client()

    _send(client, "biz_001", "isolation_customer_A", "price koto?")
    _send(client, "biz_002", "isolation_customer_B", "fade koto?")

    resp_a = client.get("/dashboard/conversations", query_string={"business_id": "biz_001"})
    ids_a = {c["customer_id"] for c in resp_a.get_json()["conversations"]}
    assert "isolation_customer_A" in ids_a
    assert "isolation_customer_B" not in ids_a

    resp_b = client.get("/dashboard/conversations", query_string={"business_id": "biz_002"})
    ids_b = {c["customer_id"] for c in resp_b.get_json()["conversations"]}
    assert "isolation_customer_B" in ids_b
    assert "isolation_customer_A" not in ids_b


def test_dashboard_conversations_needs_human_filter():
    app = create_app()
    client = app.test_client()

    _send(client, "biz_001", "angry_customer", "সার্ভিস খারাপ, রিফান্ড দেন")

    resp = client.get(
        "/dashboard/conversations",
        query_string={"business_id": "biz_001", "needs_human": "true"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    for conv in body["conversations"]:
        assert conv["human_required"] == "TRUE"
