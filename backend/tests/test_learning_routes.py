from app import create_app


def test_learning_queue_flow_via_routes():
    app = create_app()
    client = app.test_client()

    # Trigger an unknown-term detection through the normal message pipeline.
    resp = client.post(
        "/test/message",
        json={
            "business_id": "biz_001",
            "customer_id": "cust_route_test",
            "message": "gadgetxyz আছে?",
        },
    )
    assert resp.status_code == 200

    # It should now show up in the pending learning queue for that business.
    resp = client.get("/learning", query_string={"business_id": "biz_001"})
    assert resp.status_code == 200
    pending = resp.get_json()["pending"]
    matching = [e for e in pending if e["term"].lower() == "gadgetxyz"]
    assert len(matching) == 1
    learning_id = matching[0]["learning_id"]

    # Approve it with an explicit owner-provided meaning.
    resp = client.post(
        f"/learning/{learning_id}/approve",
        json={"business_id": "biz_001", "meaning": "a test gadget", "category": "misc"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "approved"
    assert body["vocabulary"]["approved"] == "TRUE"

    # It must no longer be pending.
    resp = client.get("/learning", query_string={"business_id": "biz_001"})
    remaining = [e for e in resp.get_json()["pending"] if e["term"].lower() == "gadgetxyz"]
    assert remaining == []


def test_learning_list_requires_business_id():
    app = create_app()
    client = app.test_client()
    resp = client.get("/learning")
    assert resp.status_code == 400


def test_approve_requires_meaning():
    app = create_app()
    client = app.test_client()

    client.post(
        "/test/message",
        json={
            "business_id": "biz_001",
            "customer_id": "cust_route_test2",
            "message": "thingamajig koto?",
        },
    )
    resp = client.get("/learning", query_string={"business_id": "biz_001"})
    matching = [e for e in resp.get_json()["pending"] if e["term"].lower() == "thingamajig"]
    learning_id = matching[0]["learning_id"]

    resp = client.post(f"/learning/{learning_id}/approve", json={"business_id": "biz_001"})
    assert resp.status_code == 400


def test_reject_entry_via_route():
    app = create_app()
    client = app.test_client()

    client.post(
        "/test/message",
        json={
            "business_id": "biz_001",
            "customer_id": "cust_route_test3",
            "message": "whatchamacallit ache?",
        },
    )
    resp = client.get("/learning", query_string={"business_id": "biz_001"})
    matching = [e for e in resp.get_json()["pending"] if e["term"].lower() == "whatchamacallit"]
    learning_id = matching[0]["learning_id"]

    resp = client.post(f"/learning/{learning_id}/reject", json={"business_id": "biz_001"})
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "rejected"

    resp = client.get("/learning", query_string={"business_id": "biz_001"})
    remaining = [e for e in resp.get_json()["pending"] if e["term"].lower() == "whatchamacallit"]
    assert remaining == []
