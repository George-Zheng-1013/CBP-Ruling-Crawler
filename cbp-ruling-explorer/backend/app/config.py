"""Application configuration loaded from ``backend/config.json``."""
import json
import os
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
CONFIG_FILE = Path(os.environ.get("CBP_CONFIG_FILE", BACKEND_DIR / "config.json"))
ENV_FILE = BACKEND_DIR / ".env"

_DEFAULTS: dict[str, Any] = {
    "database": {
        "cbp_path": str(BACKEND_DIR.parent.parent / "cbp-crawler" / "data" / "db" / "cbp_rulings.db"),
        "rag_index_path": str(BACKEND_DIR.parent / "data" / "rag" / "rag_index.db"),
    },
    "server": {
        "host": "127.0.0.1",
        "port": 9000,
        "cors_origins": ["http://localhost:5173"],
    },
    "crawler": {
        "python": r"D:\Develop\miniconda\envs\py312\python.exe",
        "main_dir": str(BACKEND_DIR.parent.parent / "cbp-crawler"),
        "timeout_seconds": 43200,
    },
    "models": {
        "chat": {
            "base_url": "https://api.openai.com/v1/chat/completions",
            "api_key": "",
            "model": "",
            "timeout_seconds": 120,
        },
        "embedding": {
            "base_url": "https://api.openai.com/v1/embeddings",
            "api_key": "",
            "model": "",
            "timeout_seconds": 120,
            "batch_size": 64,
        },
        "reranker": {
            "base_url": "",
            "api_key": "",
            "model": "",
            "timeout_seconds": 120,
        },
    },
    "retrieval": {
        "chunk_chars": 2400,
        "chunk_overlap": 200,
        "keyword_top_k": 40,
        "vector_top_k": 40,
        "rerank_top_k": 20,
        "evidence_top_k": 8,
        "excerpt_chars": 900,
    },
    "hts": {
        "version": "2026 Revision 11",
        "json_url": "https://www.usitc.gov/sites/default/files/tata/hts/hts_2026_revision_11_json.json",
    },
}


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if key and key not in os.environ:
                os.environ[key] = value.strip().strip('"').strip("'")


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def _load() -> dict[str, Any]:
    _load_dotenv(ENV_FILE)
    loaded: dict[str, Any] = {}
    if CONFIG_FILE.is_file():
        with CONFIG_FILE.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
    config = _merge(_DEFAULTS, loaded)

    env_map = {
        "CBP_DB_PATH": ("database", "cbp_path"),
        "RAG_INDEX_PATH": ("database", "rag_index_path"),
        "HOST": ("server", "host"),
        "PORT": ("server", "port"),
        "CRAWLER_PYTHON": ("crawler", "python"),
        "CRAWLER_MAIN_DIR": ("crawler", "main_dir"),
        "CRAWL_TIMEOUT_SECONDS": ("crawler", "timeout_seconds"),
    }
    for env_name, (section, key) in env_map.items():
        if os.environ.get(env_name):
            config[section][key] = os.environ[env_name]

    if os.environ.get("CORS_ORIGINS"):
        config["server"]["cors_origins"] = [
            value.strip()
            for value in os.environ["CORS_ORIGINS"].split(",")
            if value.strip()
        ]
    return config


def _path(value: str) -> str:
    path = Path(value)
    if not path.is_absolute():
        path = BACKEND_DIR / path
    return str(path.resolve())


CONFIG = _load()

CBP_DB_PATH: str = _path(CONFIG["database"]["cbp_path"])
RAG_INDEX_PATH: str = _path(CONFIG["database"]["rag_index_path"])
HOST: str = CONFIG["server"]["host"]
PORT: int = int(CONFIG["server"]["port"])
CORS_ORIGINS: list[str] = CONFIG["server"]["cors_origins"]

CRAWLER_PYTHON: str = CONFIG["crawler"]["python"]
CRAWLER_MAIN_DIR: str = _path(CONFIG["crawler"]["main_dir"])
CRAWLER_LOG_FILE: str = os.environ.get(
    "CRAWLER_LOG_FILE", str(Path(CRAWLER_MAIN_DIR) / "data" / "crawler.log")
)
CRAWL_TIMEOUT_SECONDS: int = int(CONFIG["crawler"]["timeout_seconds"])

CHAT_BASE_URL: str = CONFIG["models"]["chat"]["base_url"]
CHAT_API_KEY: str = CONFIG["models"]["chat"]["api_key"]
CHAT_MODEL: str = CONFIG["models"]["chat"]["model"]
CHAT_TIMEOUT_SECONDS: int = int(CONFIG["models"]["chat"]["timeout_seconds"])

EMBEDDING_BASE_URL: str = CONFIG["models"]["embedding"]["base_url"]
EMBEDDING_API_KEY: str = CONFIG["models"]["embedding"]["api_key"]
EMBEDDING_MODEL: str = CONFIG["models"]["embedding"]["model"]
EMBEDDING_TIMEOUT_SECONDS: int = int(
    CONFIG["models"]["embedding"]["timeout_seconds"]
)
EMBEDDING_BATCH_SIZE: int = int(CONFIG["models"]["embedding"]["batch_size"])

RERANKER_BASE_URL: str = CONFIG["models"]["reranker"]["base_url"]
RERANKER_API_KEY: str = CONFIG["models"]["reranker"]["api_key"]
RERANKER_MODEL: str = CONFIG["models"]["reranker"]["model"]
RERANKER_TIMEOUT_SECONDS: int = int(
    CONFIG["models"]["reranker"]["timeout_seconds"]
)

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
