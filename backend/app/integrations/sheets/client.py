"""
Thin wrapper around gspread. This is the ONLY file that talks to the Google
Sheets API directly. Everything else (repository, services) depends on the
SheetClient interface below, so Sheets can later be swapped for a real DB
without touching business logic.
"""
import logging
from typing import List, Dict, Protocol

from app.config import config

logger = logging.getLogger(__name__)


class SheetClient(Protocol):
    """Interface any data backend must satisfy."""

    def get_all_records(self, sheet_name: str) -> List[Dict]:
        ...

    def upsert_row(self, sheet_name: str, key_fields: Dict, row: Dict) -> None:
        """Find the row matching all key_fields and overwrite it with row;
        if no match exists, append row as a new one. Used for anything the
        app needs to write back (e.g. conversation memory, Phase 6)."""
        ...


class GoogleSheetsClient:
    """Real Google Sheets backend. Requires GOOGLE_SERVICE_ACCOUNT_FILE and
    GOOGLE_SPREADSHEET_ID to be set in the environment."""

    def __init__(self):
        self._spreadsheet = None

    def _connect(self):
        if self._spreadsheet is not None:
            return self._spreadsheet

        if not config.GOOGLE_SERVICE_ACCOUNT_FILE or not config.GOOGLE_SPREADSHEET_ID:
            raise RuntimeError(
                "Google Sheets not configured. Set GOOGLE_SERVICE_ACCOUNT_FILE "
                "and GOOGLE_SPREADSHEET_ID in backend/.env"
            )

        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.readonly",
        ]
        creds = Credentials.from_service_account_file(
            config.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=scopes
        )
        gc = gspread.authorize(creds)
        self._spreadsheet = gc.open_by_key(config.GOOGLE_SPREADSHEET_ID)
        return self._spreadsheet

    def get_all_records(self, sheet_name: str) -> List[Dict]:
        spreadsheet = self._connect()
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except Exception as exc:
            logger.error("Sheet tab '%s' not found: %s", sheet_name, exc)
            return []
        return worksheet.get_all_records()

    def upsert_row(self, sheet_name: str, key_fields: Dict, row: Dict) -> None:
        spreadsheet = self._connect()
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except Exception as exc:
            logger.error("Sheet tab '%s' not found: %s", sheet_name, exc)
            return

        header = worksheet.row_values(1)
        records = worksheet.get_all_records()

        for idx, existing in enumerate(records, start=2):  # row 1 is the header
            if all(str(existing.get(k, "")) == str(v) for k, v in key_fields.items()):
                merged = {**existing, **row}
                values = [merged.get(col, "") for col in header]
                worksheet.update(f"A{idx}", [values])
                return

        # No matching row — append a new one, in header column order.
        values = [row.get(col, "") for col in header]
        worksheet.append_row(values)
