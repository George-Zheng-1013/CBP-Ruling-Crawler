"""应用配置。

从 ``.env`` 文件读取配置（若存在），并暴露为模块级常量。

默认数据库路径指向既有爬虫项目的 SQLite 数据库，因此本查询服务开箱即用，
无需额外配置即可对已有裁定数据进行只读检索。
"""
import os
from typing import List

# 默认指向爬虫项目生成的 SQLite 数据库（只读消费者）。
_DEFAULT_CRAWLER_DB = (
    r"D:\HP\OneDrive\Desktop\学校\项目\生产实习\cbp-crawler\data\db\cbp_rulings.db"
)

# 后端根目录（backend/）下的 .env
ENV_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
)


def _load_dotenv(path: str) -> None:
    """读取简单的 KEY=VALUE ``.env`` 文件到环境变量。

    为避免引入第三方依赖，这里手写一个极简解析器：仅当该变量尚未存在于
    ``os.environ`` 时才写入，从而让真实环境变量优先级更高。

    Args:
        path: ``.env`` 文件的绝对路径。
    """
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv(ENV_FILE)

# ── 数据库 ──────────────────────────────────────────────────────────────────
CBP_DB_PATH: str = os.environ.get("CBP_DB_PATH", _DEFAULT_CRAWLER_DB)

# ── 服务 ────────────────────────────────────────────────────────────────────
PORT: int = int(os.environ.get("PORT", "9000"))
HOST: str = os.environ.get("HOST", "127.0.0.1")

# ── CORS ────────────────────────────────────────────────────────────────────
_CORS_ENV = os.environ.get("CORS_ORIGINS", "http://localhost:5173")
CORS_ORIGINS: List[str] = [o.strip() for o in _CORS_ENV.split(",") if o.strip()]

# ── 爬虫触发 ──────────────────────────────────────────────────────────────────
# Python 解释器路径（用于启动爬虫子进程）
CRAWLER_PYTHON: str = os.environ.get(
    "CRAWLER_PYTHON",
    r"D:\Develop\miniconda\envs\py312\python.exe"
)
# 爬虫 main.py 所在目录
CRAWLER_MAIN_DIR: str = os.environ.get(
    "CRAWLER_MAIN_DIR",
    r"D:\HP\OneDrive\Desktop\学校\项目\生产实习\cbp-crawler"
)
# 爬虫日志文件路径（共享，用于状态轮询）
CRAWLER_LOG_FILE: str = os.environ.get(
    "CRAWLER_LOG_FILE",
    os.path.join(CRAWLER_MAIN_DIR, "data", "crawler.log")
)
# 爬虫超时保护（秒）
CRAWL_TIMEOUT_SECONDS: int = int(os.environ.get("CRAWL_TIMEOUT_SECONDS", "43200"))  # 12h

# ── 分页默认 ────────────────────────────────────────────────────────────────
DEFAULT_PAGE_SIZE: int = 25
MAX_PAGE_SIZE: int = 100
