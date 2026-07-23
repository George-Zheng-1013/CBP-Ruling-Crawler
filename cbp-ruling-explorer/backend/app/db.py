"""只读 SQLite 数据访问层。

连接爬虫项目生成的 SQLite 数据库，并以 **只读** 模式打开（``mode=ro`` +
``PRAGMA query_only=1``），保证本服务绝不会对源数据库执行任何写操作。
"""
import json
import sqlite3
import threading
from typing import Any, Dict, List, Optional, Tuple

from app.config import CBP_DB_PATH


class DatabaseManager:
    """CBP rulings 数据库的只读访问器。

    由于 FastAPI 在线程池中处理请求，SQLite 连接不能在线程间共享。
    这里为每个线程维护独立（只读）连接，避免跨线程使用同一连接对象。
    """

    def __init__(self, db_path: str = CBP_DB_PATH) -> None:
        """初始化数据访问器。

        Args:
            db_path: 只读 SQLite 数据库文件路径。
        """
        self.db_path = db_path
        self._lock = threading.Lock()
        self._connections: Dict[int, sqlite3.Connection] = {}

    def connect(self) -> sqlite3.Connection:
        """打开（或复用）当前线程的只读 SQLite 连接。

        Returns:
            已设置 ``row_factory`` 的只读 ``sqlite3.Connection``。
        """
        tid = threading.get_ident()
        with self._lock:
            conn = self._connections.get(tid)
            if conn is None:
                # mode=ro + uri=True：即便代码误写也不会修改源库；
                # query_only=1 在连接级别拒绝一切非查询语句。
                uri = f"file:{self.db_path}?mode=ro"
                conn = sqlite3.connect(uri, uri=True)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA query_only=1")
                self._connections[tid] = conn
            return conn

    def close(self) -> None:
        """关闭所有线程的连接。"""
        with self._lock:
            for conn in self._connections.values():
                conn.close()
            self._connections.clear()

    def fetch_rulings(
        self,
        where_clause: str,
        bind_params: List[Any],
        page: int,
        page_size: int,
        sort: str,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """按 WHERE 条件分页查询裁定列表（含字段精简）。

        Args:
            where_clause: 参数化的 SQL 条件（不含 ``WHERE`` 关键字）。
            bind_params: 绑定到 ``where_clause`` 占位符的值列表。
            page: 从 1 起的页码。
            page_size: 每页行数。
            sort: 排序方式，取值 ``year_desc`` / ``year_asc`` / ``ruling_no``。

        Returns:
            ``(裁定字典列表, 满足过滤条件的总行数)`` 元组。
        """
        conn = self.connect()
        where_sql = f" WHERE {where_clause}" if where_clause else ""
        order_sql = self._order_clause(sort)

        count_sql = f"SELECT COUNT(*) AS cnt FROM rulings{where_sql}"
        total = conn.execute(count_sql, bind_params).fetchone()["cnt"]

        offset = (page - 1) * page_size
        data_sql = (
            "SELECT ruling_no, subject, year, hs_code, hs_codes, status, parse_failed "
            f"FROM rulings{where_sql}{order_sql} LIMIT ? OFFSET ?"
        )
        rows = conn.execute(
            data_sql, list(bind_params) + [page_size, offset]
        ).fetchall()

        result: List[Dict[str, Any]] = []
        for row in rows:
            d = dict(row)
            d["year"] = d.get("year") or 0
            d["parse_failed"] = bool(d.get("parse_failed", 0))
            result.append(d)
        return result, total

    def fetch_all_rulings(
        self, where_clause: str, bind_params: List[Any], sort: str
    ) -> List[Dict[str, Any]]:
        """返回满足过滤条件的全部裁定（不分页，用于导出）。"""
        conn = self.connect()
        where_sql = f" WHERE {where_clause}" if where_clause else ""
        order_sql = self._order_clause(sort)
        data_sql = (
            "SELECT ruling_no, subject, description, hs_code, hs_codes, year, "
            "detail_url, ruling_date, status, parse_failed, parse_error_msg "
            f"FROM rulings{where_sql}{order_sql}"
        )
        rows = conn.execute(data_sql, bind_params).fetchall()
        result: List[Dict[str, Any]] = []
        for row in rows:
            d = dict(row)
            d["parse_failed"] = bool(d.get("parse_failed", 0))
            result.append(d)
        return result

    @staticmethod
    def _order_clause(sort: str) -> str:
        """根据排序标识返回 ORDER BY 子句。"""
        if sort == "year_asc":
            return " ORDER BY year ASC, ruling_no ASC"
        if sort == "ruling_no":
            return " ORDER BY ruling_no ASC"
        return " ORDER BY year DESC, ruling_no ASC"

    def fetch_ruling_by_no(self, ruling_no: str) -> Optional[Dict[str, Any]]:
        """按裁定编号获取单条完整记录。"""
        conn = self.connect()
        row = conn.execute(
            "SELECT * FROM rulings WHERE ruling_no = ?", (ruling_no,)
        ).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["year"] = d.get("year") or 0
        d["parse_failed"] = bool(d.get("parse_failed", 0))
        try:
            d["hs_codes"] = json.loads(d.get("hs_codes") or "[]")
        except (json.JSONDecodeError, TypeError):
            d["hs_codes"] = []
        return d

    def fetch_stats(self) -> Dict[str, Any]:
        """聚合统计：总量 / 解析失败数 / 按年 / 按状态（状态动态 DISTINCT）。"""
        conn = self.connect()
        stats: Dict[str, Any] = {}
        stats["total"] = conn.execute(
            "SELECT COUNT(*) AS c FROM rulings"
        ).fetchone()["c"]
        stats["parse_failed"] = conn.execute(
            "SELECT COUNT(*) AS c FROM rulings WHERE parse_failed = 1"
        ).fetchone()["c"]
        year_rows = conn.execute(
            "SELECT year, COUNT(*) AS c FROM rulings "
            "GROUP BY year ORDER BY year DESC"
        ).fetchall()
        stats["by_year"] = [{"year": r["year"], "count": r["c"]} for r in year_rows]
        status_rows = conn.execute(
            "SELECT status, COUNT(*) AS c FROM rulings "
            "GROUP BY status ORDER BY c DESC"
        ).fetchall()
        stats["by_status"] = [
            {"status": r["status"], "count": r["c"]} for r in status_rows
        ]
        chapter_counts: Dict[str, int] = {}
        for row in conn.execute("SELECT hs_code FROM rulings WHERE hs_code IS NOT NULL"):
            digits = "".join(char for char in (row["hs_code"] or "") if char.isdigit())
            if len(digits) >= 2:
                chapter = digits[:2]
                chapter_counts[chapter] = chapter_counts.get(chapter, 0) + 1
        stats["by_chapter"] = [
            {"chapter": chapter, "count": count}
            for chapter, count in sorted(
                chapter_counts.items(), key=lambda item: (-item[1], item[0])
            )
        ]
        return stats

    def fetch_html(self, ruling_no: str) -> Optional[Dict[str, Any]]:
        """从 ``html_store`` 表获取裁定原文 HTML / 纯文本。"""
        conn = self.connect()
        row = conn.execute(
            "SELECT html_content, plain_text, fetch_status FROM html_store "
            "WHERE ruling_no = ? ORDER BY id DESC LIMIT 1",
            (ruling_no,),
        ).fetchone()
        if row is None:
            return None
        return dict(row)
