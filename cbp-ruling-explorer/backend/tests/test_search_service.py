"""SearchService.build_where / paginate 参数化单测。"""
import pytest

from app.schemas import SearchParams
from app.services.search_service import SearchService
from app.db import DatabaseManager


@pytest.mark.parametrize(
    "params,expected_where,expected_binds",
    [
        # 空参数 -> 空 WHERE + 空绑定
        (SearchParams(), "", []),
        # keyword: subject+description 双 LIKE
        (
            SearchParams(keyword="toy"),
            "(subject LIKE ? OR description LIKE ?)",
            ["%toy%", "%toy%"],
        ),
        # ruling_no 前缀匹配
        (SearchParams(ruling_no="N12"), "ruling_no LIKE ?", ["N12%"]),
        # year 精确
        (SearchParams(year=2024), "year = ?", [2024]),
        # status 精确
        (SearchParams(status="active"), "status = ?", ["active"]),
        # hs_code: 去除小数点 + 前缀
        (
            SearchParams(hs_code="8517.62"),
            "REPLACE(hs_code, '.', '') LIKE ?",
            ["851762%"],
        ),
        # 组合 AND（year + status）
        (
            SearchParams(year=2024, status="active"),
            "year = ? AND status = ?",
            [2024, "active"],
        ),
        # 全条件组合
        (
            SearchParams(keyword="a", ruling_no="N", year=2023, status="revoked", hs_code="95"),
            "(subject LIKE ? OR description LIKE ?) AND ruling_no LIKE ? AND year = ? "
            "AND status = ? AND REPLACE(hs_code, '.', '') LIKE ?",
            ["%a%", "%a%", "N%", 2023, "revoked", "95%"],
        ),
    ],
)
def test_build_where(params, expected_where, expected_binds):
    where, binds = SearchService.build_where(params)
    assert where == expected_where
    assert binds == expected_binds


def test_build_where_parameterized_no_injection():
    """hs_code 含引号等非法字符应被清洗，避免 SQL 注入。"""
    where, binds = SearchService.build_where(SearchParams(hs_code="85'; DROP TABLE rulings;--"))
    # 仅保留数字，'; DROP...' 被剥离
    assert binds == ["85%"]
    assert "DROP" not in where


def test_paginate_total_pages():
    from math import ceil

    pr = SearchService.paginate([1, 2, 3], total=23, page=2, page_size=5)
    assert pr.total == 23
    assert pr.page == 2
    assert pr.page_size == 5
    assert pr.total_pages == ceil(23 / 5)
    assert pr.items == [1, 2, 3]


def test_search_returns_pageresult(test_db_path):
    db = DatabaseManager(test_db_path)
    svc = SearchService(db)
    pr = svc.search(SearchParams(page=1, page_size=10))
    assert pr.total == 17
    assert pr.page_size == 10
    assert pr.total_pages == 2
    assert len(pr.items) == 10
    db.close()


def test_export_rows_returns_full_set_not_paginated(test_db_path):
    db = DatabaseManager(test_db_path)
    svc = SearchService(db)
    rows = svc.export_rows(SearchParams())
    assert len(rows) == 17
    # 字段完整性
    for r in rows:
        assert "ruling_no" in r and "hs_codes" in r
    db.close()
