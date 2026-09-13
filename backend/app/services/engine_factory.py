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
from app.services.learning_engine import LearningEngine
from app.integrations.gemini.client import GeminiClient
from app.integrations.facebook.client import FacebookClient, FakeFacebookClient

logger = logging.getLogger(__name__)

_pipeline: MessagePipeline | None = None
_repo: SheetsRepository | None = None
_facebook_client = None


def get_message_pipeline() -> MessagePipeline:
    global _pipeline, _repo
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
    _repo = repo
    engine = KnowledgeEngine(repo)
    memory_service = MemoryService(repo)
    order_engine = OrderEngine(engine, repo)
    learning_engine = LearningEngine(engine, repo)

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
        learning_engine=learning_engine,
    )
    return _pipeline


def get_learning_engine() -> LearningEngine:
    """Reuses the same repository/knowledge_engine as the pipeline so the
    learning queue and message pipeline are always looking at the same
    data source (real Sheets or fake, whichever get_message_pipeline set up)."""
    get_message_pipeline()
    return _pipeline._learning_engine


def get_repository() -> SheetsRepository:
    """Reuses the same repository the pipeline was built with, so the
    Facebook webhook's business lookup and the pipeline's data lookups are
    always looking at the same data source (real Sheets or fake)."""
    get_message_pipeline()
    return _repo


def get_facebook_client():
    """Real Send API client if a page access token is configured, otherwise
    a no-network fake for local dev/testing (mirrors the Gemini fallback
    pattern above — never crash the app just because a channel isn't
    configured yet)."""
    global _facebook_client
    if _facebook_client is not None:
        return _facebook_client

    if config.META_PAGE_ACCESS_TOKEN:
        _facebook_client = FacebookClient(config.META_PAGE_ACCESS_TOKEN)
        logger.info("Facebook Send API configured")
    else:
        _facebook_client = FakeFacebookClient()
        logger.warning(
            "META_PAGE_ACCESS_TOKEN not set — Facebook replies will be "
            "logged only, not actually sent."
        )
    return _facebook_client
