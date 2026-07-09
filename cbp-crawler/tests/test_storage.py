"""Tests for the storage module."""

import os
import tempfile
import json
import pytest
from storage import DatabaseManager


@pytest.fixture
def db():
    """Create a temporary database for testing."""
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test.db")
    manager = DatabaseManager(db_path)
    yield manager
    manager.close()
    # Cleanup
    try:
        os.remove(db_path)
        os.rmdir(tmp_dir)
    except OSError:
        pass


class TestDatabaseManagerInit:
    """Tests for database initialization."""

    def test_tables_exist(self, db):
        conn = db._get_connection()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row["name"] for row in cursor.fetchall()]
        assert "rulings" in tables

    def test_indexes_exist(self, db):
        conn = db._get_connection()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
        )
        indexes = [row["name"] for row in cursor.fetchall()]
        assert "idx_rulings_year" in indexes
        assert "idx_rulings_hs_code" in indexes
        assert "idx_rulings_exported" in indexes
        assert "idx_rulings_parse_failed" in indexes


class TestRulingsCRUD:
    """Tests for rulings CRUD operations."""

    def test_upsert_ruling_new(self, db):
        ruling = {
            "ruling_no": "HQ12345",
            "subject": "Classification of widgets",
            "description": "This ruling classifies widgets under heading 8471.",
            "hs_code": "8471.30.0100",
            "hs_codes": ["8471.30.0100"],
            "year": 2023,
            "detail_url": "https://rulings.cbp.gov/rulings/HQ12345",
            "ruling_date": "2023-01-15",
        }
        result = db.upsert_ruling(ruling)
        assert result is True

        fetched = db.get_ruling("HQ12345")
        assert fetched is not None
        assert fetched["ruling_no"] == "HQ12345"
        assert fetched["subject"] == "Classification of widgets"
        assert fetched["hs_code"] == "8471.30.0100"
        assert fetched["year"] == 2023

    def test_upsert_ruling_empty_ruling_no(self, db):
        ruling = {"ruling_no": ""}
        result = db.upsert_ruling(ruling)
        assert result is False

    def test_upsert_ruling_update_existing(self, db):
        # Insert first
        db.upsert_ruling({
            "ruling_no": "NY54321",
            "subject": "Original subject",
            "description": "Original description",
        })
        # Update
        db.upsert_ruling({
            "ruling_no": "NY54321",
            "subject": "Updated subject",
            "description": "Updated description",
        })
        fetched = db.get_ruling("NY54321")
        assert fetched["subject"] == "Updated subject"
        assert fetched["description"] == "Updated description"

    def test_get_ruling_not_found(self, db):
        result = db.get_ruling("NONEXISTENT")
        assert result is None

    def test_ruling_exists(self, db):
        db.upsert_ruling({"ruling_no": "OT99999"})
        assert db.ruling_exists("OT99999") is True
        assert db.ruling_exists("NONEXISTENT") is False

    def test_get_all_ruling_numbers(self, db):
        db.upsert_ruling({"ruling_no": "HQ1"})
        db.upsert_ruling({"ruling_no": "NY2"})
        db.upsert_ruling({"ruling_no": "N3"})
        all_nos = db.get_all_ruling_numbers()
        assert set(all_nos) == {"HQ1", "NY2", "N3"}

    def test_count_rulings_all(self, db):
        assert db.count_rulings() == 0
        db.upsert_ruling({"ruling_no": "HQ1"})
        db.upsert_ruling({"ruling_no": "NY2"})
        assert db.count_rulings() == 2

    def test_count_rulings_parse_failed(self, db):
        db.upsert_ruling({"ruling_no": "HQ1", "parse_failed": 1})
        db.upsert_ruling({"ruling_no": "NY2", "parse_failed": 0})
        db.upsert_ruling({"ruling_no": "N3", "parse_failed": 0})
        assert db.count_rulings(parse_failed=True) == 1
        assert db.count_rulings(parse_failed=False) == 2

    def test_hs_codes_json_serialization(self, db):
        hs_codes = ["8471.30.0100", "8471.30.0110"]
        db.upsert_ruling({
            "ruling_no": "HQ99999",
            "hs_codes": hs_codes,
        })
        fetched = db.get_ruling("HQ99999")
        # hs_codes stored as JSON string
        stored = json.loads(fetched["hs_codes"])
        assert stored == hs_codes

    def test_hs_codes_list_input(self, db):
        """Test that passing a list for hs_codes works."""
        hs_codes = ["8471.30.0100"]
        db.upsert_ruling({
            "ruling_no": "HQ88888",
            "hs_codes": hs_codes,
        })
        fetched = db.get_ruling("HQ88888")
        stored = json.loads(fetched["hs_codes"])
        assert stored == hs_codes


class TestMarkExported:
    """Tests for marking rulings as exported."""

    def test_mark_exported(self, db):
        db.upsert_ruling({"ruling_no": "HQ12345"})
        db.mark_exported("HQ12345")
        fetched = db.get_ruling("HQ12345")
        assert fetched["is_exported"] == 1

    def test_get_unexported_rulings(self, db):
        db.upsert_ruling({"ruling_no": "HQ1"})
        db.upsert_ruling({"ruling_no": "NY2"})
        db.mark_exported("HQ1")
        unexported = db.get_unexported_rulings()
        ruling_nos = [r["ruling_no"] for r in unexported]
        assert "HQ1" not in ruling_nos
        assert "NY2" in ruling_nos


class TestGetStatistics:
    """Tests for get_statistics method."""

    def test_empty_stats(self, db):
        stats = db.get_statistics()
        assert stats["total_rulings"] == 0
        assert stats["parsed_ok"] == 0
        assert stats["parse_failed"] == 0
        assert stats["exported"] == 0

    def test_stats_with_data(self, db):
        db.upsert_ruling({"ruling_no": "HQ1", "parse_failed": 0})
        db.upsert_ruling({"ruling_no": "NY2", "parse_failed": 0})
        db.upsert_ruling({"ruling_no": "N3", "parse_failed": 1})
        db.mark_exported("HQ1")

        stats = db.get_statistics()
        assert stats["total_rulings"] == 3
        assert stats["parsed_ok"] == 2
        assert stats["parse_failed"] == 1
        assert stats["exported"] == 1


class TestContextManager:
    """Tests for DatabaseManager as context manager."""

    def test_context_manager_closes_connection(self):
        tmp_dir = tempfile.mkdtemp()
        db_path = os.path.join(tmp_dir, "test_ctx.db")
        with DatabaseManager(db_path) as db:
            db.upsert_ruling({"ruling_no": "HQ1"})
            assert db.get_ruling("HQ1") is not None
        # Connection should be closed after exit
        assert db._connection is None
        # Cleanup
        try:
            os.remove(db_path)
            os.rmdir(tmp_dir)
        except OSError:
            pass
