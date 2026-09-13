from app import create_app


def test_test_message_endpoint_happy_path():
    app = create_app()
    client = app.test_client()
    resp = client.post(
        "/test/message",
        json={
            "business_id": "biz_001",
            "customer_id": "cust_1",
            "message": "black shirt XL আছে?",
        },
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["intent"] == "AVAILABILITY_INQUIRY"
    assert "entities" in body
    assert "retrieved_data" in body
    assert "confidence" in body
    assert "response" in body


def test_test_message_endpoint_missing_fields():
    app = create_app()
    client = app.test_client()
    resp = client.post("/test/message", json={"business_id": "biz_001"})
    assert resp.status_code == 400
