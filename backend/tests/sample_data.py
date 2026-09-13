"""
Re-exports the canonical sample data from app.integrations.sheets.sample_data
so both app code (local-dev fallback) and tests use the exact same fixture.
"""
from app.integrations.sheets.sample_data import SAMPLE_SHEETS  # noqa: F401
