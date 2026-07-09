"""SQLite database operations for the CBP Advance Ruling Crawler.

Manages structured ruling data (rulings table) retrieved from the CROSS
JSON API. Provides connection handling, schema creation, and CRUD operations.
"""

import sqlite3
import json
import os
from typing import Optional, List, Dict, Any

from config import DB_FILENAME
from utils import setup_logger

logger = setup_logger("storage")


class DatabaseManager:
    """Manages SQLite database connections and schema migrations.

    Provides thread-safe connection handling and ensures all required
    tables and indexes exist on initialization.
    """

    def __init__(self, db_path: str = DB_FILENAME) -> None:
        """Initialize the database manager and create tables/indexes.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
        self._initialize()

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create a persistent SQLite connection.

        Returns:
            sqlite3.Connection object with row factory set.
        """
        if self._connection is None:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA foreign_keys=ON")
        return self._connection

    def _initialize(self) -> None:
        """Create all required tables and indexes if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # ── Rulings table (structured data) ──
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rulings (
                ruling_no       TEXT PRIMARY KEY,
                subject         TEXT DEFAULT '',
                description     TEXT DEFAULT '',
                hs_code         TEXT DEFAULT '',
                hs_codes        TEXT DEFAULT '[]',
                year            INTEGER,
                detail_url      TEXT DEFAULT '',
                ruling_date     TEXT DEFAULT '',
                status          TEXT DEFAULT 'active',
                parse_failed    INTEGER DEFAULT 0,
                parse_error_msg TEXT DEFAULT '',
                is_exported     INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            )
        """)

        # ── Indexes ──
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rulings_year ON rulings(year)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rulings_hs_code ON rulings(hs_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rulings_exported ON rulings(is_exported)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rulings_parse_failed ON rulings(parse_failed)")

        conn.commit()

    def close(self) -> None:
        """Close the database connection if open."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def __enter__(self) -> "DatabaseManager":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit — close the connection."""
        self.close()

    # ── Rulings CRUD ─────────────────────────────────────────────────────────

    def upsert_ruling(self, ruling: Dict[str, Any]) -> bool:
        """Insert or update a ruling record.

        Args:
            ruling: Dict with keys matching the rulings table columns.
                    Must include at least 'ruling_no'.

        Returns:
            True if the operation succeeded, False otherwise.
        """
        try:
            conn = self._get_connection()
            ruling_no = ruling.get("ruling_no", "").strip()
            if not ruling_no:
                logger.warning("Attempted to upsert ruling with empty ruling_no")
                return False

            existing = self.get_ruling(ruling_no)
            hs_codes_raw = ruling.get("hs_codes", "[]")
            if isinstance(hs_codes_raw, list):
                hs_codes_raw = json.dumps(hs_codes_raw)

            if existing:
                # Update existing
                conn.execute(
                    """
                    UPDATE rulings SET
                        subject = ?,
                        description = ?,
                        hs_code = ?,
                        hs_codes = ?,
                        year = ?,
                        detail_url = ?,
                        ruling_date = ?,
                        status = ?,
                        parse_failed = ?,
                        parse_error_msg = ?,
                        updated_at = datetime('now')
                    WHERE ruling_no = ?
                    """,
                    (
                        ruling.get("subject", existing.get("subject", "")),
                        ruling.get("description", existing.get("description", "")),
                        ruling.get("hs_code", existing.get("hs_code", "")),
                        hs_codes_raw,
                        ruling.get("year", existing.get("year")),
                        ruling.get("detail_url", existing.get("detail_url", "")),
                        ruling.get("ruling_date", existing.get("ruling_date", "")),
                        ruling.get("status", existing.get("status", "active")),
                        ruling.get("parse_failed", existing.get("parse_failed", 0)),
                        ruling.get("parse_error_msg", existing.get("parse_error_msg", "")),
                        ruling_no,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO rulings (
                        ruling_no, subject, description, hs_code, hs_codes,
                        year, detail_url, ruling_date, status, parse_failed,
                        parse_error_msg
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ruling_no,
                        ruling.get("subject", ""),
                        ruling.get("description", ""),
                        ruling.get("hs_code", ""),
                        hs_codes_raw,
                        ruling.get("year"),
                        ruling.get("detail_url", ""),
                        ruling.get("ruling_date", ""),
                        ruling.get("status", "active"),
                        ruling.get("parse_failed", 0),
                        ruling.get("parse_error_msg", ""),
                    ),
                )
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error("Database error upserting ruling %s: %s",
                         ruling.get("ruling_no", "?"), str(e))
            return False

    def get_ruling(self, ruling_no: str) -> Optional[Dict[str, Any]]:
        """Fetch a ruling by its ruling number.

        Args:
            ruling_no: The ruling number to look up.

        Returns:
            Dict of ruling data or None if not found.
        """
        try:
            conn = self._get_connection()
            cursor = conn.execute(
                "SELECT * FROM rulings WHERE ruling_no = ?", (ruling_no,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        except sqlite3.Error as e:
            logger.error("Database error fetching ruling %s: %s", ruling_no, str(e))
            return None

    def ruling_exists(self, ruling_no: str) -> bool:
        """Check if a ruling number already exists in the database.

        Args:
            ruling_no: The ruling number to check.

        Returns:
            True if the ruling exists, False otherwise.
        """
        return self.get_ruling(ruling_no) is not None

    def get_all_ruling_numbers(self) -> List[str]:
        """Return all stored ruling numbers.

        Returns:
            List of ruling number strings.
        """
        try:
            conn = self._get_connection()
            cursor = conn.execute("SELECT ruling_no FROM rulings")
            return [row["ruling_no"] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error("Database error fetching all ruling numbers: %s", str(e))
            return []

    def count_rulings(self, parse_failed: Optional[bool] = None) -> int:
        """Count rulings, optionally filtered by parse_failed status.

        Args:
            parse_failed: If True, count only parse-failed rulings.
                          If False, count only successfully parsed rulings.
                          If None, count all rulings.

        Returns:
            Integer count of matching rulings.
        """
        try:
            conn = self._get_connection()
            if parse_failed is True:
                cursor = conn.execute(
                    "SELECT COUNT(*) AS cnt FROM rulings WHERE parse_failed = 1"
                )
            elif parse_failed is False:
                cursor = conn.execute(
                    "SELECT COUNT(*) AS cnt FROM rulings WHERE parse_failed = 0"
                )
            else:
                cursor = conn.execute("SELECT COUNT(*) AS cnt FROM rulings")
            row = cursor.fetchone()
            return row["cnt"] if row else 0
        except sqlite3.Error as e:
            logger.error("Database error counting rulings: %s", str(e))
            return 0

    def clear_rulings(self) -> int:
        """Delete every row from the rulings table (fresh re-crawl).

        Returns:
            Number of rows deleted.
        """
        try:
            conn = self._get_connection()
            cursor = conn.execute("DELETE FROM rulings")
            deleted = cursor.rowcount
            conn.commit()
            conn.execute("VACUUM")
            logger.info("Cleared rulings table (%d rows deleted)", deleted)
            return deleted
        except sqlite3.Error as e:
            logger.error("Database error clearing rulings: %s", str(e))
            return 0

    def mark_exported(self, ruling_no: str) -> None:
        """Mark a ruling as exported.

        Args:
            ruling_no: The ruling number to mark.
        """
        try:
            conn = self._get_connection()
            conn.execute(
                "UPDATE rulings SET is_exported = 1, updated_at = datetime('now') "
                "WHERE ruling_no = ?",
                (ruling_no,),
            )
            conn.commit()
        except sqlite3.Error as e:
            logger.error("Database error marking ruling %s as exported: %s",
                         ruling_no, str(e))

    def get_unexported_rulings(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Fetch rulings that have not yet been exported.

        Args:
            limit: Maximum number of records to return.

        Returns:
            List of ruling dicts.
        """
        try:
            conn = self._get_connection()
            cursor = conn.execute(
                "SELECT * FROM rulings WHERE is_exported = 0 ORDER BY year DESC, ruling_no "
                "LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error("Database error fetching unexported rulings: %s", str(e))
            return []

    # ── Statistics ───────────────────────────────────────────────────────────

    def get_statistics(self) -> Dict[str, Any]:
        """Return summary statistics about the database contents.

        Returns:
            Dict with keys: total_rulings, parsed_ok, parse_failed, exported.
        """
        stats: Dict[str, Any] = {}
        conn = self._get_connection()

        try:
            cursor = conn.execute("SELECT COUNT(*) AS cnt FROM rulings")
            stats["total_rulings"] = cursor.fetchone()["cnt"]
        except sqlite3.Error:
            stats["total_rulings"] = 0

        try:
            cursor = conn.execute(
                "SELECT COUNT(*) AS cnt FROM rulings WHERE parse_failed = 0"
            )
            stats["parsed_ok"] = cursor.fetchone()["cnt"]
        except sqlite3.Error:
            stats["parsed_ok"] = 0

        try:
            cursor = conn.execute(
                "SELECT COUNT(*) AS cnt FROM rulings WHERE parse_failed = 1"
            )
            stats["parse_failed"] = cursor.fetchone()["cnt"]
        except sqlite3.Error:
            stats["parse_failed"] = 0

        try:
            cursor = conn.execute(
                "SELECT COUNT(*) AS cnt FROM rulings WHERE is_exported = 1"
            )
            stats["exported"] = cursor.fetchone()["cnt"]
        except sqlite3.Error:
            stats["exported"] = 0

        return stats
