"""
In-memory stand-in for GoogleSheetsClient. Same interface (get_all_records,
upsert_row), so repository/services code doesn't know or care which one
it's using. Used for tests and for local development before Google
credentials exist.
"""
from copy import deepcopy
from typing import List, Dict, Optional


class FakeSheetsClient:
    def __init__(self, data: Optional[Dict[str, List[Dict]]] = None):
        # data = {"PRODUCTS": [ {...row...}, ... ], "BUSINESSES": [...] }
        # Deep-copied so writes (upsert_row) never mutate a shared fixture
        # (e.g. a module-level SAMPLE_SHEETS dict reused across tests).
        self._data = deepcopy(data) if data else {}

    def get_all_records(self, sheet_name: str) -> List[Dict]:
        return self._data.get(sheet_name, [])

    def upsert_row(self, sheet_name: str, key_fields: Dict, row: Dict) -> None:
        rows = self._data.setdefault(sheet_name, [])
        for existing in rows:
            if all(str(existing.get(k, "")) == str(v) for k, v in key_fields.items()):
                existing.update(row)
                return
        rows.append(dict(row))
