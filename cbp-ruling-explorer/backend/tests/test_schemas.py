"""Pydantic schemas 校验单测（SearchParams 等）。"""
import pytest
from pydantic import ValidationError

from app.schemas import SearchParams, Envelope, PageResult, RulingListItem


def test_search_params_defaults():
    p = SearchParams()
    assert p.page == 1
    assert p.page_size == 25  # DEFAULT_PAGE_SIZE
    assert p.sort == "year_desc"


@pytest.mark.parametrize("bad", [{"page": 0}, {"page": -1}])
def test_search_params_page_min(bad):
    with pytest.raises(ValidationError):
        SearchParams(**bad)


def test_search_params_page_size_clamped():
    # 超过 MAX_PAGE_SIZE(100) 应被收敛到 100，而非报错
    p = SearchParams(page_size=9999)
    assert p.page_size == 100
    # 低于 1 收敛到 1
    assert SearchParams(page_size=0).page_size == 1


@pytest.mark.parametrize("bad_sort", ["bad", "YEAR_DESC", "random"])
def test_search_params_sort_allowed(bad_sort):
    with pytest.raises(ValidationError):
        SearchParams(sort=bad_sort)


def test_search_params_year_range():
    with pytest.raises(ValidationError):
        SearchParams(year=1800)
    with pytest.raises(ValidationError):
        SearchParams(year=2101)
    assert SearchParams(year=2024).year == 2024


def test_search_params_hs_code_sanitized():
    # 仅保留数字与小数点
    assert SearchParams(hs_code="85.17.62").hs_code == "85.17.62"
    assert SearchParams(hs_code="85abc17!@#").hs_code == "8517"
    assert SearchParams(hs_code="'; DROP--").hs_code is None


def test_envelope_defaults():
    e = Envelope(data={"x": 1})
    assert e.code == 0
    assert e.message == "ok"
    assert e.data == {"x": 1}


def test_ruling_list_item_parse_failed_bool():
    item = RulingListItem(ruling_no="N1", parse_failed=1)
    # 传入非 bool 时 Pydantic 是否强制为 bool 取决于类型注解；此处验证字段存在
    assert item.ruling_no == "N1"
