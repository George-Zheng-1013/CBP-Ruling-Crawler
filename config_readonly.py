"""Application configuration loaded directly from ``backend/config.json``."""
import json
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
CONFIG_FILE = Path(os.environ.get("CBP_CONFIG_FILE", BACKEND_DIR / "config.json"))

with CONFIG_FILE.open("r", encoding="utf-8") as handle:
    CONFIG = json.load(handle)


def _path(value: str) -> str:
    path = Path(value)
    if not path.is_absolute():
        path = BACKEND_DIR / path
    return str(path.resolve())


CBP_DB_PATH: str = _path(CONFIG["database"]["cbp_path"])
RAG_INDEX_PATH: str = _path(CONFIG["database"]["rag_index_path"])
HOST: str = CONFIG["server"]["host"]
PORT: int = int(CONFIG["server"]["port"])
CORS_ORIGINS: list[str] = CONFIG["server"]["cors_origins"]

CRAWLER_PYTHON: str = CONFIG["crawler"]["python"]
CRAWLER_MAIN_DIR: str = _path(CONFIG["crawler"]["main_dir"])
CRAWLER_LOG_FILE: str = str(Path(CRAWLER_MAIN_DIR) / "data" / "crawler.log")
CRAWL_TIMEOUT_SECONDS: int = int(CONFIG["crawler"]["timeout_seconds"])

CHAT_BASE_URL: str = CONFIG["models"]["chat"]["base_url"].rstrip("/")
CHAT_API_KEY: str = CONFIG["models"]["chat"]["api_key"]
CHAT_MODEL: str = CONFIG["models"]["chat"]["model"]
CHAT_TIMEOUT_SECONDS: int = int(CONFIG["models"]["chat"]["timeout_seconds"])

EMBEDDING_BASE_URL: str = CONFIG["models"]["embedding"]["base_url"].rstrip("/")
EMBEDDING_API_KEY: str = CONFIG["models"]["embedding"]["api_key"]
EMBEDDING_MODEL: str = CONFIG["models"]["embedding"]["model"]
EMBEDDING_TIMEOUT_SECONDS: int = int(
    CONFIG["models"]["embedding"]["timeout_seconds"]
)
EMBEDDING_BATCH_SIZE: int = int(CONFIG["models"]["embedding"]["batch_size"])

RAG_CHUNK_CHARS: int = int(CONFIG["retrieval"]["chunk_chars"])
RAG_CHUNK_OVERLAP: int = int(CONFIG["retrieval"]["chunk_overlap"])
RAG_KEYWORD_TOP_K: int = int(CONFIG["retrieval"]["keyword_top_k"])
RAG_VECTOR_TOP_K: int = int(CONFIG["retrieval"]["vector_top_k"])
RAG_RERANK_TOP_K: int = int(CONFIG["retrieval"]["rerank_top_k"])
RAG_EVIDENCE_TOP_K: int = int(CONFIG["retrieval"]["evidence_top_k"])
RAG_EXCERPT_CHARS: int = int(CONFIG["retrieval"]["excerpt_chars"])

HTS_VERSION: str = CONFIG["hts"]["version"]
HTS_JSON_URL: str = CONFIG["hts"]["json_url"]

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100
