"""
Central configuration. All secrets/config come from environment variables.
Never hard-code credentials here.
"""
import os
from dotenv import load_dotenv

load_dotenv()  # loads backend/.env if present


class Config:
    # App
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Google Sheets (filled in Phase 2)
    GOOGLE_SERVICE_ACCOUNT_FILE: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "")
    GOOGLE_SPREADSHEET_ID: str = os.getenv("GOOGLE_SPREADSHEET_ID", "")

    # Gemini AI (Phase 5)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # Facebook Messenger (filled in Phase 10)
    META_APP_SECRET: str = os.getenv("META_APP_SECRET", "")
    META_PAGE_ACCESS_TOKEN: str = os.getenv("META_PAGE_ACCESS_TOKEN", "")
    META_VERIFY_TOKEN: str = os.getenv("META_VERIFY_TOKEN", "")

    # WhatsApp (filled in Phase 11)
    WHATSAPP_ACCESS_TOKEN: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

    # Owner/dashboard API protection (Phase 14). When set, every owner-facing
    # endpoint (dashboard, learning queue, follow-up, /test/message) requires
    # header "X-API-Key: <this value>". Never enforced against webhooks —
    # those are authenticated by Meta's own signature instead.
    OWNER_API_KEY: str = os.getenv("OWNER_API_KEY", "")

    # Simple in-memory rate limiting (Phase 14). Zero-cost/local-first, so
    # no external rate-limiting service — just a per-process request cap.
    # Good enough for a single-instance deployment; a multi-instance
    # deployment would need a shared store instead.
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    @classmethod
    def is_production(cls) -> bool:
        return cls.APP_ENV == "production"


config = Config()
