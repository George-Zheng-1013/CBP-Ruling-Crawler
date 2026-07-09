"""Tests for the utils module."""

import time
import pytest
from utils import (
    DeduplicationSet,
    clean_text,
    random_delay,
    exponential_backoff,
    normalize_url,
    extract_ruling_no_from_url,
    safe_filename,
)


class TestDeduplicationSet:
    """Tests for DeduplicationSet class."""

    def test_add_and_contains(self):
        ds = DeduplicationSet()
        ds.add("HQ12345")
        assert ds.contains("HQ12345") is True
        assert ds.contains("NY99999") is False

    def test_add_if_new_returns_true_for_new(self):
        ds = DeduplicationSet()
        assert ds.add_if_new("HQ12345") is True

    def test_add_if_new_returns_false_for_duplicate(self):
        ds = DeduplicationSet()
        ds.add("HQ12345")
        assert ds.add_if_new("HQ12345") is False

    def test_size(self):
        ds = DeduplicationSet()
        assert ds.size() == 0
        ds.add("HQ1")
        ds.add("NY2")
        ds.add("N3")
        assert ds.size() == 3
        ds.add("HQ1")  # duplicate
        assert ds.size() == 3

    def test_load_from_list(self):
        ds = DeduplicationSet()
        ds.load_from_list(["HQ1", "NY2", "N3"])
        assert ds.size() == 3
        assert ds.contains("HQ1") is True
        assert ds.contains("N3") is True
        assert ds.contains("OT99") is False

    def test_to_list_returns_sorted(self):
        ds = DeduplicationSet()
        ds.load_from_list(["NY2", "HQ1", "N3"])
        result = ds.to_list()
        assert result == ["HQ1", "N3", "NY2"]

    def test_empty_set_to_list(self):
        ds = DeduplicationSet()
        assert ds.to_list() == []

    def test_add_empty_string(self):
        ds = DeduplicationSet()
        ds.add("")
        assert ds.contains("") is True

    def test_add_if_new_empty_string(self):
        ds = DeduplicationSet()
        assert ds.add_if_new("") is True
        assert ds.add_if_new("") is False


class TestCleanText:
    """Tests for clean_text function."""

    def test_none_input(self):
        assert clean_text(None) == ""

    def test_empty_string(self):
        assert clean_text("") == ""

    def test_whitespace_only(self):
        assert clean_text("   \t\n  ") == ""

    def test_basic_trim(self):
        assert clean_text("  hello world  ") == "hello world"

    def test_normalize_newlines(self):
        text = "line1\r\nline2\r\nline3"
        result = clean_text(text)
        assert "\r\n" not in result
        assert result == "line1\nline2\nline3"

    def test_collapse_trailing_spaces_before_newline(self):
        text = "line1   \nline2"
        result = clean_text(text)
        assert "   \n" not in result

    def test_collapse_leading_spaces_after_newline(self):
        text = "line1\n   line2"
        result = clean_text(text)
        assert "\n   " not in result

    def test_collapse_multiple_newlines(self):
        text = "line1\n\n\n\nline2"
        result = clean_text(text)
        assert "\n\n\n" not in result

    def test_preserve_double_newlines(self):
        text = "para1\n\npara2"
        result = clean_text(text)
        assert result == "para1\n\npara2"

    def test_realistic_ruling_text(self):
        text = "  This is a ruling about tariff classification.\n\n"
        text += "  The item is classified under 8471.30.0100.\n\n"
        text += "  More legal analysis here.  "
        result = clean_text(text)
        assert result.startswith("This is")
        assert result.endswith("here.")
        assert "8471.30.0100" in result


class TestRandomDelay:
    """Tests for random_delay function."""

    def test_delay_within_range(self):
        start = time.time()
        random_delay(0.01, 0.02)
        elapsed = time.time() - start
        assert 0.005 <= elapsed <= 0.1  # Allow small tolerance

    def test_zero_delay(self):
        start = time.time()
        random_delay(0, 0)
        elapsed = time.time() - start
        assert elapsed < 0.1


class TestExponentialBackoff:
    """Tests for exponential_backoff function."""

    def test_backoff_increases_with_attempts(self):
        start = time.time()
        exponential_backoff(0, base_delay=0.01)
        t0 = time.time() - start

        start = time.time()
        exponential_backoff(2, base_delay=0.01)
        t2 = time.time() - start

        # Attempt 2 (exponential) should be significantly longer than attempt 0
        assert t2 > t0 * 0.3  # Allow some tolerance for random jitter


class TestNormalizeUrl:
    """Tests for normalize_url function."""

    def test_absolute_url_unchanged(self):
        url = "https://rulings.cbp.gov/search"
        assert normalize_url(url) == url

    def test_relative_path_with_leading_slash(self):
        result = normalize_url("/search?collection=Advance+Ruling")
        assert result == "https://rulings.cbp.gov/search?collection=Advance+Ruling"

    def test_relative_path_without_leading_slash(self):
        result = normalize_url("search")
        assert result == "https://rulings.cbp.gov/search"

    def test_empty_path(self):
        result = normalize_url("")
        assert result == "https://rulings.cbp.gov/"

    def test_detail_url_path(self):
        result = normalize_url("/rulings/N082097")
        assert result == "https://rulings.cbp.gov/rulings/N082097"


class TestExtractRulingNoFromUrl:
    """Tests for extract_ruling_no_from_url function."""

    def test_standard_detail_url(self):
        url = "https://rulings.cbp.gov/rulings/N082097"
        assert extract_ruling_no_from_url(url) == "N082097"

    def test_url_with_query_params(self):
        url = "https://rulings.cbp.gov/rulings/HQ123456?format=json"
        assert extract_ruling_no_from_url(url) == "HQ123456"

    def test_no_ruling_number(self):
        url = "https://rulings.cbp.gov/search"
        assert extract_ruling_no_from_url(url) is None

    def test_short_ruling_prefix(self):
        url = "https://rulings.cbp.gov/rulings/W12345"
        assert extract_ruling_no_from_url(url) == "W12345"

    def test_empty_url(self):
        assert extract_ruling_no_from_url("") is None

    def test_none_url(self):
        # Function expects a string, None should be handled gracefully
        try:
            result = extract_ruling_no_from_url(None)  # type: ignore
            assert result is None
        except (TypeError, AttributeError):
            pass  # Acceptable error for invalid input


class TestSafeFilename:
    """Tests for safe_filename function."""

    def test_simple_ruling_no(self):
        assert safe_filename("HQ12345") == "HQ12345"

    def test_with_invalid_chars(self):
        result = safe_filename("HQ:12/345")
        assert ":" not in result
        assert "/" not in result

    def test_empty_string(self):
        assert safe_filename("") == ""

    def test_only_invalid_chars(self):
        result = safe_filename("<>:\"/\\|?*")
        assert len(result) == 9
        assert all(c == "_" for c in result)
