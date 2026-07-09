"""DatabaseManager 只读保障与查询逻辑单测。"""
import sqlite3

import pytest

from app.db import DatabaseManager


def test_readonly_connection_rejects_writes(test_db_path):
    """关键：只读连接（mode=ro + query_only=1）必须拒绝一切写操作。"""
    db = DatabaseManager(test_db_path)
    conn = db.connect()
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("INSERT INTO rulings (ruling_no) VALUES ('SHOULD_FAIL')")
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("UPDATE rulings SET subject = 'x' WHERE ruling_no = 'N12345'")
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("DELETE FROM rulings WHERE ruling_no = 'N12345'")
    db.close()


def test_fetch_rulings_list_and_pagination(test_db_path):
    db = DatabaseManager(test_db_path)
    rows, total = db.fetch_rulings("", [], page=1, page_size=5, sort="year_desc")
    assert total == 17
    assert len(rows) == 5
    # 字段精简集合
    assert set(rows[0].keys()) == {
        "ruling_no", "subject", "year", "hs_code", "status", "parse_failed"
    }
    # parse_failed 被强制为 bool
    for r in rows:
        assert isinstance(r["parse_failed"], bool)
    db.close()


def test_fetch_rulings_sort_year_asc(test_db_path):
    db = DatabaseManager(test_db_path)
    rows, _ = db.fetch_rulings("", [], page=1, page_size=100, sort="year_asc")
    years = [r["year"] for r in rows]
    assert years == sorted(years)
    db.close()


def test_fetch_ruling_by_no_full_detail(test_db_path):
    db = DatabaseManager(test_db_path)
    row = db.fetch_ruling_by_no("N12345")
    assert row is not None
    assert row["ruling_no"] == "N12345"
    assert row["description"]  # 详情含全文
    assert row["detail_url"]
    # hs_codes 应被解析为 list
    assert isinstance(row["hs_codes"], list)
    assert "9503.00.0000" in row["hs_codes"]
    # 不存在返回 None
    assert db.fetch_ruling_by_no("DOES_NOT_EXIST") is None
    db.close()


def test_fetch_ruling_parse_failed_flag(test_db_path):
    db = DatabaseManager(test_db_path)
    row = db.fetch_ruling_by_no("N33333")
    assert row["parse_failed"] is True
    assert row["parse_error_msg"]  # 解析失败条目带错误信息
    db.close()


def test_fetch_stats_matches_raw_sql(test_db_path):
    db = DatabaseManager(test_db_path)
    stats = db.fetch_stats()
    raw = sqlite3.connect(test_db_path)
    raw.row_factory = sqlite3.Row
    total = raw.execute("SELECT COUNT(*) c FROM rulings").fetchone()["c"]
    pf = raw.execute("SELECT COUNT(*) c FROM rulings WHERE parse_failed=1").fetchone()["c"]
    by_year = [dict(r) for r in raw.execute(
        "SELECT year, COUNT(*) c FROM rulings GROUP BY year ORDER BY year DESC")]
    by_status = [dict(r) for r in raw.execute(
        "SELECT status, COUNT(*) c FROM rulings GROUP BY status ORDER BY c DESC")]
    raw.close()

    assert stats["total"] == total
    assert stats["parse_failed"] == pf
    # 结构一致
    assert [{"year": y["year"], "count": y["c"]} for y in by_year] == stats["by_year"]
    assert [{"status": s["status"], "count": s["c"]} for s in by_status] == stats["by_status"]
    db.close()


def test_fetch_html_missing_returns_none(test_db_path):
    db = DatabaseManager(test_db_path)
    # 测试库未注入 html_store 数据，应返回 None（P2 容忍空）
    assert db.fetch_html("N12345") is None
    db.close()
