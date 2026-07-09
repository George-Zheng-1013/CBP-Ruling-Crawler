"""Pydantic 模型：请求校验与响应序列化。

所有响应模型使用 snake_case 字段命名，前端通过 ``api/client.ts`` 的拦截器
自动转换为 camelCase。
"""
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field, field_validator

from app.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

ALLOWED_SORTS = ("year_desc", "year_asc", "ruling_no")


class SearchParams(BaseModel):
    """列表/导出接口的查询参数。"""

    keyword: Optional[str] = None
    ruling_no: Optional[str] = None
    year: Optional[int] = None
    status: Optional[str] = None
    hs_code: Optional[str] = None
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE
    sort: str = "year_desc"

    @field_validator("page")
    @classmethod
    def _check_page(cls, v: int) -> int:
        if v < 1:
            raise ValueError("page must be >= 1")
        return v

    @field_validator("page_size")
    @classmethod
    def _check_page_size(cls, v: int) -> int:
        return max(1, min(v, MAX_PAGE_SIZE))

    @field_validator("sort")
    @classmethod
    def _check_sort(cls, v: str) -> str:
        if v not in ALLOWED_SORTS:
            raise ValueError(f"sort must be one of {ALLOWED_SORTS}")
        return v

    @field_validator("hs_code")
    @classmethod
    def _sanitize_hs_code(cls, v: Optional[str]) -> Optional[str]:
        # 仅保留数字与小数点，去除其它字符（防注入的同时做归一化）。
        if v is None:
            return None
        cleaned = "".join(ch for ch in v if ch.isdigit() or ch == ".")
        return cleaned or None

    @field_validator("year")
    @classmethod
    def _check_year(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1900 <= v <= 2100):
            raise ValueError("year out of range")
        return v


class RulingListItem(BaseModel):
    """列表项（字段精简）。"""

    ruling_no: str
    subject: str = ""
    year: int = 0
    hs_code: str = ""
    status: str = "active"
    parse_failed: bool = False


class RulingDetail(RulingListItem):
    """详情项（继承列表项并扩展全文/链接/解析信息）。"""

    description: str = ""
    hs_codes: List[str] = Field(default_factory=list)
    ruling_date: str = ""
    detail_url: str = ""
    parse_error_msg: str = ""


class YearCount(BaseModel):
    """按年份计数。"""

    year: int
    count: int


class StatusCount(BaseModel):
    """按状态计数。"""

    status: str
    count: int


class StatsOverview(BaseModel):
    """统计概览。"""

    total: int = 0
    parse_failed: int = 0
    by_year: List[YearCount] = Field(default_factory=list)
    by_status: List[StatusCount] = Field(default_factory=list)


T = TypeVar("T")


class PageResult(BaseModel, Generic[T]):
    """分页包装。"""

    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class HtmlContent(BaseModel):
    """裁定原文 HTML。"""

    html_content: str = ""
    plain_text: str = ""
    fetch_status: int = 200


class Envelope(BaseModel, Generic[T]):
    """统一响应信封。"""

    code: int = 0
    message: str = "ok"
    data: Optional[T] = None


# ── 爬虫触发 ─────────────────────────────────────────────────────────────────


class CrawlSyncRequest(BaseModel):
    """全库同步请求体。"""

    min_date: str = Field(..., description="起始日期，ISO 格式 YYYY-MM-DD")

    @field_validator("min_date")
    @classmethod
    def _check_date(cls, v: str) -> str:
        import re
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("min_date must be ISO format YYYY-MM-DD")
        y, m, d = v.split("-")
        if not (2000 <= int(y) <= 2030 and 1 <= int(m) <= 12 and 1 <= int(d) <= 31):
            raise ValueError("min_date out of reasonable range")
        return v


class CrawlJobStatus(BaseModel):
    """爬虫任务状态。"""

    status: str = "idle"  # idle | running | completed | failed
    min_date: str = ""
    pid: Optional[int] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    log_tail: str = ""


class CrawlStartResponse(BaseModel):
    """启动爬虫的即时响应。"""

    status: str  # started | conflict
    min_date: str
    message: str = ""
