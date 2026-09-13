import pytest

from app import create_app
from app.config import config


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config, "OWNER_API_KEY", "test-owner-key")
    app = create_app()
    return app.test_client()


def _auth():
    return {"X-API-Key": "test-owner-key"}


def test_create_business_happy_path(client):
    resp = client.post(
        "/dashboard/businesses",
        json={
            "business_name": "New Client Shop",
            "business_type": "clothing",
            "phone": "01700000099",
            "currency": "BDT",
            "default_language": "bn",
        },
        headers=_auth(),
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["status"] == "created"
    assert body["business"]["business_name"] == "New Client Shop"
    assert body["business"]["business_id"].startswith("biz_")

    # The new business should now be independently readable/lookupable.
    business_id = body["business"]["business_id"]
    get_resp = client.get(f"/dashboard/settings?business_id={business_id}", headers=_auth())
    assert get_resp.status_code == 200
    assert get_resp.get_json()["settings"]["business_name"] == "New Client Shop"


def test_create_business_missing_fields(client):
    resp = client.post("/dashboard/businesses", json={"business_name": "No Type Shop"}, headers=_auth())
    assert resp.status_code == 400


def test_create_business_requires_owner_key(client):
    resp = client.post(
        "/dashboard/businesses",
        json={"business_name": "X", "business_type": "salon"},
    )
    assert resp.status_code == 401


def test_two_created_businesses_get_different_ids(client):
    r1 = client.post(
        "/dashboard/businesses",
        json={"business_name": "Shop A", "business_type": "clothing"},
        headers=_auth(),
    )
    r2 = client.post(
        "/dashboard/businesses",
        json={"business_name": "Shop B", "business_type": "restaurant"},
        headers=_auth(),
    )
    id1 = r1.get_json()["business"]["business_id"]
    id2 = r2.get_json()["business"]["business_id"]
    assert id1 != id2
