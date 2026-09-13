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

    # Facebook Messenger (filled in Phase 10)
    META_APP_SECRET: str = os.getenv("META_APP_SECRET", "")
    META_PAGE_ACCESS_TOKEN: str = os.getenv("META_PAGE_ACCESS_TOKEN", "")
    META_VERIFY_TOKEN: str = os.getenv("META_VERIFY_TOKEN", "")

    # WhatsApp (filled in Phase 11)
    WHATSAPP_ACCESS_TOKEN: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

    @classmethod
    def is_production(cls) -> bool:
        return cls.APP_ENV == "production"


config = Config()
