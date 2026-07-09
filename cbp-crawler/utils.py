"""Utility functions for the CBP Advance Ruling Crawler.

Provides logging setup, request delay helpers, deduplication helpers,
and general-purpose utility routines.
"""

import logging
import os
import random
import time
import re
from typing import Optional, Set, List, Dict, Any

from config import (
    LOG_LEVEL,
    LOG_FORMAT,
    LOG_DATE_FORMAT,
    LOG_FILE,
    MIN_DELAY,
    MAX_DELAY,
)


# ── Logging ──────────────────────────────────────────────────────────────────


def setup_logger(name: str = "cbp-crawler") -> logging.Logger:
    """Configure and return a logger instance with both file and console handlers.

    Args:
        name: Logger name (default: 'cbp-crawler').

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    # Prevent duplicate handlers when called multiple times
    if logger.handlers:
        return logger

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # File handler
    log_dir = os.path.dirname(LOG_FILE)
    os.makedirs(log_dir, exist_ok=True)
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger


# ── Rate Limiting ────────────────────────────────────────────────────────────


def random_delay(min_delay: float = MIN_DELAY, max_delay: float = MAX_DELAY) -> None:
    """Sleep for a random duration between min_delay and max_delay seconds.

    Args:
        min_delay: Minimum delay in seconds.
        max_delay: Maximum delay in seconds.
    """
    delay = random.uniform(min_delay, max_delay)
    time.sleep(delay)


def exponential_backoff(attempt: int, base_delay: float = 1.5) -> None:
    """Sleep with exponential backoff based on retry attempt count.

    Args:
        attempt: Current retry attempt number (0-based).
        base_delay: Base delay multiplier in seconds.
    """
    delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
    time.sleep(delay)


# ── Deduplication ────────────────────────────────────────────────────────────


class DeduplicationSet:
    """Thread-safe in-memory deduplication set for ruling numbers.

    Tracks seen ruling numbers to avoid processing duplicates across tasks.
    """

    def __init__(self) -> None:
        """Initialize an empty deduplication set."""
        self._seen: Set[str] = set()

    def add(self, ruling_no: str) -> None:
        """Mark a ruling number as seen.

        Args:
            ruling_no: The ruling number to add.
        """
        self._seen.add(ruling_no)

    def contains(self, ruling_no: str) -> bool:
        """Check if a ruling number has already been seen.

        Args:
            ruling_no: The ruling number to check.

        Returns:
            True if already seen, False otherwise.
        """
        return ruling_no in self._seen

    def add_if_new(self, ruling_no: str) -> bool:
        """Add a ruling number if not already seen.

        Args:
            ruling_no: The ruling number to add.

        Returns:
            True if newly added, False if already existed.
        """
        if ruling_no in self._seen:
            return False
        self._seen.add(ruling_no)
        return True

    def size(self) -> int:
        """Return the number of unique ruling numbers tracked.

        Returns:
            Current count of unique ruling numbers.
        """
        return len(self._seen)

    def load_from_list(self, ruling_numbers: List[str]) -> None:
        """Bulk load ruling numbers into the deduplication set.

        Args:
            ruling_numbers: List of ruling numbers to load.
        """
        for rn in ruling_numbers:
            self._seen.add(rn)

    def to_list(self) -> List[str]:
        """Export all tracked ruling numbers as a list.

        Returns:
            Sorted list of all ruling numbers.
        """
        return sorted(self._seen)


# ── URL Helpers ──────────────────────────────────────────────────────────────


def normalize_url(path: str) -> str:
    """Join a relative path with the CBP base URL.

    Args:
        path: Relative URL path (e.g., '/search?collection=Advance+Ruling').

    Returns:
        Fully qualified URL.
    """
    from config import CBP_BASE_URL

    if path.startswith("http"):
        return path
    if path.startswith("/"):
        return f"{CBP_BASE_URL}{path}"
    return f"{CBP_BASE_URL}/{path}"


def extract_ruling_no_from_url(url: str) -> Optional[str]:
    """Extract a ruling number from a CBP detail page URL.

    Args:
        url: The CBP URL to extract from.

    Returns:
        Ruling number string if found, None otherwise.
    """
    # Pattern: /rulings/.../HQ123456 or similar
    match = re.search(r"/rulings/[^/]+/([A-Z]{1,3}\d{2,6})(?:\?|$|/)", url)
    if match:
        return match.group(1)
    # Pattern: the last path segment looks like a ruling number
    match = re.search(r"/([A-Z]{1,3}\d{2,6})(?:\?|$|/)", url)
    if match:
        return match.group(1)
    return None


# ── String Helpers ───────────────────────────────────────────────────────────


def clean_text(text: Optional[str]) -> str:
    """Strip whitespace, normalize newlines, and collapse multiple spaces.

    Args:
        text: Raw input text (may be None).

    Returns:
        Cleaned text string, or empty string if input is None.
    """
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r" +\n", "\n", text)
    text = re.sub(r"\n +", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def safe_filename(ruling_no: str) -> str:
    """Convert a ruling number into a safe filesystem filename.

    Args:
        ruling_no: Ruling number string.

    Returns:
        Filesystem-safe filename (without extension).
    """
    safe = re.sub(r'[<>:"/\\|?*]', "_", ruling_no)
    return safe.strip()
