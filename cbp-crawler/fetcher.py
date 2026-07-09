"""HTTP fetching module for the CBP Advance Ruling Crawler.

Fetches structured JSON from the official CROSS JSON API
(https://rulings.cbp.gov/api). The public site is an Angular SPA whose static
HTML is an empty shell, so all data is retrieved via these JSON endpoints — no
HTML scraping or browser automation is performed.
"""

import requests
from typing import Optional, Dict, Any
from urllib.parse import urlencode, quote

from config import (
    USER_AGENT,
    REQUEST_TIMEOUT,
    REQUEST_MAX_RETRIES,
    CBP_BASE_URL,
    CBP_API_SEARCH_URL,
    CBP_API_RULING_URL,
    API_PAGE_SIZE,
    API_SORT_BY,
)
from utils import (
    setup_logger,
    random_delay,
    exponential_backoff,
)

logger = setup_logger("fetcher")


class JsonResult:
    """Holds the result of a JSON API fetch.

    Attributes:
        url: The URL that was fetched.
        data: The parsed JSON payload (dict/list) or None on failure.
        status_code: HTTP status code (0 if unknown/error).
        error_message: Error description if the fetch failed.
    """

    def __init__(self, url: str, data: Any = None, status_code: int = 0,
                 error_message: str = "") -> None:
        self.url = url
        self.data = data
        self.status_code = status_code
        self.error_message = error_message

    def success(self) -> bool:
        """Return True if a JSON payload was retrieved with a 2xx status."""
        return self.data is not None and 200 <= self.status_code < 300

    def __repr__(self) -> str:
        kind = type(self.data).__name__ if self.data is not None else "None"
        return (f"JsonResult(url={self.url}, status={self.status_code}, "
                f"data={kind}, error={self.error_message})")


def _build_json_headers() -> Dict[str, str]:
    """Build HTTP headers for CROSS JSON API requests.

    Returns:
        Dict of HTTP headers requesting a JSON response.
    """
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": f"{CBP_BASE_URL}/search",
    }


def fetch_json(url: str, timeout: int = REQUEST_TIMEOUT,
               max_retries: int = REQUEST_MAX_RETRIES) -> JsonResult:
    """Fetch a JSON payload from a CROSS API endpoint.

    Uses the requests library with retry + exponential backoff.

    Args:
        url: The API URL to fetch.
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retry attempts.

    Returns:
        JsonResult with the parsed payload (or an error).
    """
    session = requests.Session()
    session.headers.update(_build_json_headers())

    last_error = ""
    for attempt in range(max_retries + 1):
        try:
            response = session.get(url, timeout=timeout, allow_redirects=True)
            if response.status_code == 200:
                try:
                    payload = response.json()
                except ValueError as e:
                    last_error = f"Invalid JSON: {e}"
                    logger.warning("Non-JSON response from %s: %s", url, e)
                    if attempt < max_retries:
                        exponential_backoff(attempt)
                    continue
                random_delay()
                return JsonResult(url=url, data=payload,
                                  status_code=response.status_code)
            elif response.status_code == 429:
                wait_time = 10 * (attempt + 1)
                logger.warning("Rate limited (429) for %s, waiting %ds",
                               url, wait_time)
                import time
                time.sleep(wait_time)
                last_error = "HTTP 429 (rate limited)"
            elif response.status_code == 404:
                # A missing ruling is a definitive answer, not worth retrying.
                random_delay()
                return JsonResult(url=url, data=None,
                                  status_code=404,
                                  error_message="HTTP 404 (not found)")
            elif response.status_code == 403:
                logger.warning("Forbidden (403) for %s", url)
                return JsonResult(url=url, data=None, status_code=403,
                                  error_message="HTTP 403 (forbidden)")
            else:
                last_error = f"HTTP {response.status_code}"
                logger.warning("Unexpected status %d for %s (attempt %d)",
                               response.status_code, url, attempt)
                if attempt < max_retries:
                    exponential_backoff(attempt)

        except requests.exceptions.Timeout:
            last_error = "Request timeout"
            logger.warning("Timeout fetching %s (attempt %d/%d)",
                           url, attempt + 1, max_retries)
            if attempt < max_retries:
                exponential_backoff(attempt)

        except requests.exceptions.ConnectionError:
            last_error = "Connection error"
            logger.warning("Connection error fetching %s (attempt %d/%d)",
                           url, attempt + 1, max_retries)
            if attempt < max_retries:
                exponential_backoff(attempt)

        except requests.exceptions.RequestException as e:
            last_error = str(e)
            logger.warning("Request exception for %s: %s (attempt %d/%d)",
                           url, e, attempt + 1, max_retries)
            if attempt < max_retries:
                exponential_backoff(attempt)

    return JsonResult(url=url, data=None, status_code=0,
                      error_message=last_error)


def build_api_search_url(term: str, page: int = 1,
                         page_size: int = API_PAGE_SIZE,
                         collection: Optional[str] = None,
                         sort_by: str = API_SORT_BY) -> str:
    """Build a CROSS JSON search URL.

    Args:
        term: The search term (e.g., an HTS chapter code like '85' or '8517').
              Must be non-empty — the API returns zero results for empty terms.
        page: 1-based page number.
        page_size: Results per page (API supports up to 250).
        collection: Optional collection filter ('ny' or 'hq').
        sort_by: Sort mode (default 'RELEVANCE').

    Returns:
        Fully qualified JSON search URL.
    """
    query_params: Dict[str, Any] = {
        "term": term,
        "pageSize": page_size,
        "page": max(1, page),
        "sortBy": sort_by,
    }
    if collection:
        query_params["collection"] = collection
    return f"{CBP_API_SEARCH_URL}?{urlencode(query_params)}"


def build_api_ruling_url(ruling_number: str) -> str:
    """Build the CROSS JSON detail URL for a specific ruling.

    Args:
        ruling_number: The ruling number (e.g., 'N316829').

    Returns:
        Fully qualified JSON detail URL.
    """
    return f"{CBP_API_RULING_URL}/{quote(ruling_number.strip())}"
