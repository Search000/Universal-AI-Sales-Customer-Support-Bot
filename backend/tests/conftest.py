"""
Test isolation from the local developer's real .env file.

Without this, a developer who has filled in real GOOGLE_SERVICE_ACCOUNT_FILE,
GOOGLE_SPREADSHEET_ID, OWNER_API_KEY, GEMINI_API_KEY, or platform tokens for
manual testing would have every single test in this suite silently start
hitting the real Google Sheet, the real Gemini API, and requiring the real
owner key — causing quota errors, unrelated failures, and tests that behave
differently on every machine.

This autouse fixture resets config to safe, deterministic test defaults
before every test, and clears engine_factory's cached singletons so each
test rebuilds a fresh, fake-backed pipeline. Individual tests remain free
to monkeypatch any of these back on for the specific behavior they want
to test (see test_phase14_security.py for examples).
"""
import pytest

from app.config import config
from app.services import engine_factory


@pytest.fixture(autouse=True)
def _isolate_from_real_env(monkeypatch):
    monkeypatch.setattr(config, "OWNER_API_KEY", "")
    monkeypatch.setattr(config, "GOOGLE_SERVICE_ACCOUNT_FILE", "")
    monkeypatch.setattr(config, "GOOGLE_SPREADSHEET_ID", "")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    monkeypatch.setattr(config, "META_APP_SECRET", "")
    monkeypatch.setattr(config, "META_PAGE_ACCESS_TOKEN", "")
    monkeypatch.setattr(config, "META_VERIFY_TOKEN", "")
    monkeypatch.setattr(config, "WHATSAPP_ACCESS_TOKEN", "")
    monkeypatch.setattr(config, "WHATSAPP_PHONE_NUMBER_ID", "")

    engine_factory.reset_for_tests()
    yield
    engine_factory.reset_for_tests()
