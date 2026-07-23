import sqlite3

from app.db import DatabaseManager


def test_stats_group_primary_hts_code_by_chapter(tmp_path):
    path = tmp_path / "stats.db"
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE rulings (
            hs_code TEXT, parse_failed INTEGER, year INTEGER, status TEXT
        )
        """
    )
    conn.executemany(
        "INSERT INTO rulings VALUES (?, ?, ?, ?)",
        [
            ("8544.42.9090", 0, 2025, "active"),
            ("8517.62.0090", 0, 2025, "active"),
            ("3926.90.9989", 0, 2024, "active"),
            ("", 1, 2024, "revoked"),
        ],
    )
    conn.commit()
    conn.close()

    stats = DatabaseManager(str(path)).fetch_stats()

    assert stats["by_chapter"] == [
        {"chapter": "85", "count": 2},
        {"chapter": "39", "count": 1},
    ]
