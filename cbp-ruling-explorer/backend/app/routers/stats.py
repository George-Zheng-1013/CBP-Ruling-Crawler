"""统计概览端点。"""
from fastapi import APIRouter

from app.db import DatabaseManager
from app.schemas import Envelope, StatusCount, StatsOverview, YearCount

router = APIRouter(prefix="/api/stats", tags=["stats"])

_db = DatabaseManager()


@router.get("/overview", summary="统计概览")
def stats_overview() -> Envelope[StatsOverview]:
    """返回总量 / 解析失败数 / 按年 / 按状态（状态动态 DISTINCT）。"""
    raw = _db.fetch_stats()
    overview = StatsOverview(
        total=raw["total"],
        parse_failed=raw["parse_failed"],
        by_year=[YearCount(**y) for y in raw["by_year"]],
        by_status=[StatusCount(**s) for s in raw["by_status"]],
    )
    return Envelope(data=overview)
