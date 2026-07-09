"""搜索/过滤条件拼装与分页辅助。

``build_where`` 将经过校验的 ``SearchParams`` 转换为 **参数化** 的 WHERE 子句，
所有取值均以绑定参数传入，从根上杜绝 SQL 注入。排序/分页逻辑集中在此，
便于后续在 P2 阶段替换为 FTS5 匹配策略而不改动 API 契约。
"""
from math import ceil
from typing import Any, List, Tuple

from app.db import DatabaseManager
from app.schemas import PageResult, SearchParams


class SearchService:
    """将查询参数翻译为 SQL 并对结果分页。"""

    def __init__(self, db: DatabaseManager) -> None:
        """构造搜索服务。

        Args:
            db: 只读数据库访问器。
        """
        self._db = db

    @staticmethod
    def build_where(params: SearchParams) -> Tuple[str, List[Any]]:
        """构建参数化 WHERE 子句。

        Args:
            params: 已校验的查询参数。

        Returns:
            ``(不含 WHERE 关键字的 WHERE 条件, 绑定值列表)`` 元组。
        """
        conditions: List[str] = []
        binds: List[Any] = []

        if params.keyword:
            # 关键词匹配 subject + description，LIKE 值两侧加 %。
            like = f"%{params.keyword}%"
            conditions.append("(subject LIKE ? OR description LIKE ?)")
            binds.extend([like, like])

        if params.ruling_no:
            # 裁定编号前缀匹配。
            conditions.append("ruling_no LIKE ?")
            binds.append(f"{params.ruling_no}%")

        if params.year is not None:
            conditions.append("year = ?")
            binds.append(params.year)

        if params.status:
            conditions.append("status = ?")
            binds.append(params.status)

        if params.hs_code:
            # 主 hs_code 前缀匹配；忽略小数点，使 "8517" 也能命中 "8517.62.0090"。
            digits = "".join(ch for ch in params.hs_code if ch.isdigit())
            conditions.append("REPLACE(hs_code, '.', '') LIKE ?")
            binds.append(f"{digits}%")

        where = " AND ".join(conditions)
        return where, binds

    def search(self, params: SearchParams) -> PageResult:
        """执行过滤 + 分页搜索，返回 PageResult。"""
        where, binds = self.build_where(params)
        rows, total = self._db.fetch_rulings(
            where, binds, params.page, params.page_size, params.sort
        )
        return self.paginate(rows, total, params.page, params.page_size)

    def export_rows(self, params: SearchParams) -> List[dict]:
        """返回当前过滤条件的全部行（不分页，供导出使用）。"""
        where, binds = self.build_where(params)
        return self._db.fetch_all_rulings(where, binds, params.sort)

    @staticmethod
    def paginate(
        rows: List[Any], total: int, page: int, page_size: int
    ) -> PageResult:
        """将行与元数据包装为 PageResult。"""
        total_pages = ceil(total / page_size) if page_size else 0
        return PageResult(
            items=rows,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
