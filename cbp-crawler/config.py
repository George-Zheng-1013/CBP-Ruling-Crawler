"""Global configuration for the CBP Advance Ruling Crawler.

This module defines all configurable parameters including request intervals,
User-Agent strings, file paths, and runtime behavior constants.

The crawler consumes the official CROSS JSON API (https://rulings.cbp.gov/api)
which returns structured records directly — no HTML scraping is performed.
"""

import os
from typing import Tuple, List

# ── Project Paths ────────────────────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
DB_DIR = os.path.join(DATA_DIR, "db")

# Ensure runtime directories exist
for _dir in (DATA_DIR, DB_DIR):
    os.makedirs(_dir, exist_ok=True)

# ── Database ─────────────────────────────────────────────────────────────────
DB_FILENAME = os.path.join(DB_DIR, "cbp_rulings.db")

# ── HTTP / Requests ──────────────────────────────────────────────────────────
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

REQUEST_TIMEOUT: int = 30  # seconds
REQUEST_MAX_RETRIES: int = 3
REQUEST_RETRY_BACKOFF: float = 1.5  # multiplier

CBP_BASE_URL = "https://rulings.cbp.gov"

# ── CROSS JSON API (hidden but stable endpoints backing the Angular SPA) ──────
# The public site is an Angular single-page app whose static HTML is an empty
# shell; the real data is served by these JSON endpoints.
#   Search : GET {CBP_API_SEARCH_URL}?term=<t>&pageSize=<n>&page=<p>&sortBy=RELEVANCE
#            -> {"rulings": [ {...} ], "totalHits": <int>}
#   Detail : GET {CBP_API_RULING_URL}/{rulingNumber}
#            -> { ..., "text": "<full ruling text>", "url": "/docs/..." }
CBP_API_BASE_URL = f"{CBP_BASE_URL}/api"
CBP_API_SEARCH_URL = f"{CBP_API_BASE_URL}/search"
CBP_API_RULING_URL = f"{CBP_API_BASE_URL}/ruling"

# ── Rate Limiting ────────────────────────────────────────────────────────────
MIN_DELAY: float = 2.0   # minimum delay between requests (seconds)
MAX_DELAY: float = 5.0   # maximum delay between requests (seconds)

# ── Search Sharding Dimensions ───────────────────────────────────────────────
YEAR_RANGE: Tuple[int, int] = (2000, 2026)

HTS_CHAPTERS: List[str] = [f"{i:02d}" for i in range(1, 98)]  # 01-97

# ── CROSS JSON API crawl settings ────────────────────────────────────────────
# The API accepts pageSize up to 250 and has no obvious hard page cap.
API_PAGE_SIZE: int = 250
API_SORT_BY: str = "RELEVANCE"          # server sort mode (RELEVANCE works)
# Only `DATE_DESC` actually sorts newest-first (all other values behave like
# RELEVANCE on this API). Used for date-bounded crawls so we can stop paging
# as soon as we pass the min-date threshold.
API_SORT_BY_DATE_DESC: str = "DATE_DESC"
API_MAX_PAGES_PER_TERM: int = 200       # safety cap per enumeration term
# Enumeration terms: HTS chapter codes (01-97) used as the search `term`.
# Each HTS code, when used as a term, enumerates all rulings tagged under it,
# which is how we walk the full corpus without a browsable index.
API_SEARCH_TERMS: List[str] = HTS_CHAPTERS

# ── Extraction / Parsing ─────────────────────────────────────────────────────
HSCODE_PATTERN = r"\b(\d{4}\.\d{2}\.\d{4})\b"
RULING_NO_PATTERN = r"\b([A-Z]{1,3}\d{2,6})\b"
YEAR_PATTERN = r"\b(20\d{2})\b"

# ── Export ───────────────────────────────────────────────────────────────────
EXPORT_FIELD_SEPARATOR: str = "|"
EXPORT_ENCODING: str = "utf-8"
EXPORT_FILENAME = os.path.join(DATA_DIR, "cbp_rulings_export.txt")

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_LEVEL: str = "INFO"
LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
LOG_FILE = os.path.join(DATA_DIR, "crawler.log")
