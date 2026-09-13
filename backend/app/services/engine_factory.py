"""
Builds the single shared MessagePipeline instance the API uses.
Picks a real Google Sheets client if configured, otherwise falls back to
in-memory sample data for local testing (Phase 4 has no real Sheets
connection required yet).
"""
import logging

from app.config import config
from app.integrations.sheets.client import GoogleSheetsClient
from app.integrations.sheets.fake_client import FakeSheetsClient
from app.integrations.sheets.repository import SheetsRepository
from app.integrations.sheets.sample_data import SAMPLE_SHEETS
from app.services.knowledge_engine import KnowledgeEngine
from app.services.message_pipeline import MessagePipeline
from app.services.memory_service import MemoryService
from app.services.order_engine import OrderEngine
from app.integrations.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

_pipeline: MessagePipeline | None = None


def get_message_pipeline() -> MessagePipeline:
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    if config.GOOGLE_SERVICE_ACCOUNT_FILE and config.GOOGLE_SPREADSHEET_ID:
        client = GoogleSheetsClient()
        logger.info("Using real Google Sheets as data source")
    else:
        client = FakeSheetsClient(SAMPLE_SHEETS)
        logger.warning(
            "GOOGLE_SHEETS not configured — using built-in sample data. "
            "This is for local testing only, not real business data."
        )

    repo = SheetsRepository(client)
    engine = KnowledgeEngine(repo)
    memory_service = MemoryService(repo)
    order_engine = OrderEngine(engine, repo)

    gemini_client = None
    if config.GEMINI_API_KEY:
        try:
            gemini_client = GeminiClient(config.GEMINI_API_KEY, config.GEMINI_MODEL)
            logger.info("Gemini AI phrasing enabled (model=%s)", config.GEMINI_MODEL)
        except Exception:
            logger.exception("Failed to init Gemini client — falling back to deterministic responses")
    else:
        logger.warning("GEMINI_API_KEY not set — using deterministic template responses only")

    _pipeline = MessagePipeline(
        engine,
        gemini_client=gemini_client,
        memory_service=memory_service,
        order_engine=order_engine,
    )
    return _pipeline
