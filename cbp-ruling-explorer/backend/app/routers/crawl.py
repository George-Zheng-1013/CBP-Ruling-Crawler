"""爬虫触发与状态查询路由。

提供三个端点：
- POST /api/crawl/incremental   — 增量更新（从最新裁定日期起抓取）
- POST /api/crawl/sync          — 全库同步（用户指定起始日期）
- GET  /api/crawl/status        — 查询当前（或最近一次）任务状态

爬虫通过子进程异步执行，避免阻塞 API 响应。同一时间只允许运行一个爬虫任务。
"""

import os
import subprocess
import threading
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException

from app.config import (
    CBP_DB_PATH,
    CRAWLER_PYTHON,
    CRAWLER_MAIN_DIR,
    CRAWLER_LOG_FILE,
    CRAWL_TIMEOUT_SECONDS,
)
from app.schemas import (
    Envelope,
    CrawlSyncRequest,
    CrawlJobStatus,
    CrawlStartResponse,
)

router = APIRouter(prefix="/api/crawl", tags=["crawl"])

# ── 任务状态单例 ────────────────────────────────────────────────────────────

_job_lock = threading.Lock()
_job: Dict[str, Any] = {
    "status": "idle",       # idle | running | completed | failed
    "pid": None,
    "min_date": "",
    "started_at": None,
    "completed_at": None,
    "error_message": None,
    "process": None,        # subprocess.Popen | None
    "thread": None,         # threading.Thread | None
}


def _tail_log(filepath: str, n: int = 20) -> str:
    """读取日志文件最后 n 行。"""
    if not os.path.isfile(filepath):
        return ""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
        tail = "".join(lines[-n:])
        return tail.rstrip()
    except (OSError, IOError):
        return ""


def _build_job_status() -> CrawlJobStatus:
    """构造当前任务状态响应。"""
    with _job_lock:
        return CrawlJobStatus(
            status=_job["status"],
            min_date=_job["min_date"],
            pid=_job["pid"],
            started_at=_job["started_at"],
            completed_at=_job["completed_at"],
            error_message=_job["error_message"],
            log_tail=_tail_log(CRAWLER_LOG_FILE),
        )


def _detect_latest_date() -> Optional[str]:
    """从数据库中查询最新的 ruling_date，返回 ISO 字符串。"""
    try:
        import sqlite3
        conn = sqlite3.connect(CBP_DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT MAX(ruling_date) AS md FROM rulings WHERE ruling_date IS NOT NULL AND ruling_date != ''"
        ).fetchone()
        md = row["md"] if row else None
        conn.close()
        return md
    except Exception:
        return None


def _run_crawl(min_date: str) -> None:
    """在后台线程中执行爬虫子进程。"""
    cmd = [
        CRAWLER_PYTHON,
        "main.py",
        "--phase", "api",
        "--min-date", min_date,
        "--series", "hq", "ny",
    ]

    with _job_lock:
        _job["status"] = "running"
        _job["min_date"] = min_date
        _job["started_at"] = datetime.now().isoformat(timespec="seconds")
        _job["error_message"] = None
        _job["completed_at"] = None

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=CRAWLER_MAIN_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        with _job_lock:
            _job["pid"] = proc.pid
            _job["process"] = proc

        # 等待进程结束（带超时保护）
        try:
            proc.wait(timeout=CRAWL_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            with _job_lock:
                _job["status"] = "failed"
                _job["error_message"] = f"Timed out after {CRAWL_TIMEOUT_SECONDS // 3600}h"
                _job["completed_at"] = datetime.now().isoformat(timespec="seconds")
            return

        # 检查退出码
        if proc.returncode == 0:
            with _job_lock:
                _job["status"] = "completed"
                _job["completed_at"] = datetime.now().isoformat(timespec="seconds")
        else:
            # 读取最后的错误输出
            output = ""
            try:
                if proc.stdout:
                    output = proc.stdout.read()[-2000:]
            except Exception:
                pass
            with _job_lock:
                _job["status"] = "failed"
                _job["error_message"] = f"Exit code {proc.returncode}. Last output:\n{output[:500]}"
                _job["completed_at"] = datetime.now().isoformat(timespec="seconds")

    except Exception as exc:
        with _job_lock:
            _job["status"] = "failed"
            _job["error_message"] = str(exc)
            _job["completed_at"] = datetime.now().isoformat(timespec="seconds")
    finally:
        with _job_lock:
            _job["pid"] = None
            _job["process"] = None
            _job["thread"] = None


# ── 起始端点 ────────────────────────────────────────────────────────────────


@router.post("/incremental", response_model=Envelope[CrawlStartResponse])
def start_incremental():
    """增量更新：从库中最新裁定日期当天起爬取。"""
    with _job_lock:
        if _job["status"] == "running":
            raise HTTPException(
                status_code=409,
                detail={"code": 1, "message": "A crawl job is already running", "data": None},
            )

    # 检测最新日期
    latest = _detect_latest_date()
    if not latest:
        # 库为空，默认从 2025-01-01 起
        latest = "2025-01-01"
    min_date = latest[:10]

    # 启动后台线程
    thread = threading.Thread(target=_run_crawl, args=(min_date,), daemon=True)
    with _job_lock:
        _job["thread"] = thread
    thread.start()

    return Envelope(data=CrawlStartResponse(
        status="started",
        min_date=min_date,
        message=f"Incremental crawl started from {min_date}",
    ))


@router.post("/sync", response_model=Envelope[CrawlStartResponse])
def start_sync(body: CrawlSyncRequest):
    """全库同步：从指定日期起检查并同步所有裁定。"""
    with _job_lock:
        if _job["status"] == "running":
            raise HTTPException(
                status_code=409,
                detail={"code": 1, "message": "A crawl job is already running", "data": None},
            )

    min_date = body.min_date

    thread = threading.Thread(target=_run_crawl, args=(min_date,), daemon=True)
    with _job_lock:
        _job["thread"] = thread
    thread.start()

    return Envelope(data=CrawlStartResponse(
        status="started",
        min_date=min_date,
        message=f"Full sync crawl started from {min_date}",
    ))


@router.get("/status", response_model=Envelope[CrawlJobStatus])
def get_status():
    """查询当前爬虫任务状态。"""
    return Envelope(data=_build_job_status())
