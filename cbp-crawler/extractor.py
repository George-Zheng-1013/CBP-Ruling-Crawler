"""JSON extraction for CBP CROSS search results and ruling details.

Parses the structured JSON returned by the official CROSS API endpoints
(see fetcher.fetch_json). Output dicts use the same keys as the SQLite
``rulings`` table so they can be handed straight to
DatabaseManager.upsert_ruling().
"""

from typing import List, Dict, Any, Optional

from utils import setup_logger, clean_text

logger = setup_logger("extractor")

CBP_SITE_BASE = "https://rulings.cbp.gov"


def map_ruling_json(record: Dict[str, Any],
                    include_text: bool = False) -> Dict[str, Any]:
    """Map a CROSS JSON ruling record to the storage schema.

    Args:
        record: A single ruling dict from /api/search (list item) or
                /api/ruling/{no} (detail).
        include_text: If True, populate 'description' from the detail 'text'
                      field (only present on the detail endpoint).

    Returns:
        Dict with keys aligned to the rulings table: ruling_no, subject,
        description (only when include_text), hs_code, hs_codes, year,
        ruling_date, status, detail_url, collection.
    """
    record = record or {}
    ruling_no = str(record.get("rulingNumber") or "").strip().upper()

    # tariffs -> HS codes (already in XXXX.XX.XXXX form, e.g. "8537.10.9170")
    raw_tariffs = record.get("tariffs") or []
    hs_codes: List[str] = []
    seen: set = set()
    for t in raw_tariffs:
        code = str(t).strip()
        if code and code not in seen:
            seen.add(code)
            hs_codes.append(code)

    # rulingDate is ISO like "2021-01-20T00:00:00"
    raw_date = str(record.get("rulingDate") or "")
    ruling_date = raw_date[:10] if len(raw_date) >= 10 else raw_date
    year: Optional[int] = None
    if len(raw_date) >= 4 and raw_date[:4].isdigit():
        year = int(raw_date[:4])

    # Status: revoked if there are revoking rulings or an operational revocation
    revoked = bool(record.get("revokedBy")) or bool(record.get("operationallyRevoked"))
    status = "revoked" if revoked else "active"

    mapped: Dict[str, Any] = {
        "ruling_no": ruling_no,
        "subject": clean_text(record.get("subject") or ""),
        "hs_code": hs_codes[0] if hs_codes else "",
        "hs_codes": hs_codes,
        "year": year,
        "ruling_date": ruling_date,
        "status": status,
        "detail_url": f"{CBP_SITE_BASE}/ruling/{ruling_no}" if ruling_no else "",
        "collection": str(record.get("collection") or "").upper(),
    }
    if include_text:
        mapped["description"] = clean_text(record.get("text") or "")
    return mapped


class JsonSearchExtractor:
    """Extracts ruling summaries from a CROSS /api/search JSON payload.

    The payload shape is: {"rulings": [ {...}, ... ], "totalHits": <int>}.
    """

    def __init__(self, data: Any) -> None:
        """Initialize with the parsed JSON payload.

        Args:
            data: The dict returned by /api/search.
        """
        self.data = data if isinstance(data, dict) else {}

    def total_hits(self) -> Optional[int]:
        """Return the total number of hits reported by the API, if present."""
        value = self.data.get("totalHits")
        try:
            return int(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    def extract_items(self) -> List[Dict[str, Any]]:
        """Extract mapped ruling summary records from the search payload.

        Returns:
            List of dicts (storage-aligned, without 'description'). Records
            missing a ruling number are skipped.
        """
        rulings = self.data.get("rulings")
        if not isinstance(rulings, list):
            logger.debug("Search payload has no 'rulings' list")
            return []

        items: List[Dict[str, Any]] = []
        for record in rulings:
            if not isinstance(record, dict):
                continue
            mapped = map_ruling_json(record, include_text=False)
            if mapped["ruling_no"]:
                items.append(mapped)
        return items


class JsonDetailExtractor:
    """Extracts full structured content from a CROSS /api/ruling JSON payload."""

    def __init__(self, data: Any) -> None:
        """Initialize with the parsed JSON detail payload.

        Args:
            data: The dict returned by /api/ruling/{rulingNumber}.
        """
        self.data = data if isinstance(data, dict) else {}

    def extract_all(self) -> Dict[str, Any]:
        """Extract all fields including the full ruling text.

        Returns:
            Dict with keys: ruling_no, subject, description, hs_code,
            hs_codes, year, ruling_date, status, detail_url, collection.
        """
        return map_ruling_json(self.data, include_text=True)
