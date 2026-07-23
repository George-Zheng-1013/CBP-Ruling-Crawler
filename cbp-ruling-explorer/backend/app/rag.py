"""Lightweight CBP ruling RAG index, retrieval, and classification service."""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import re
import sqlite3
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from app.config import (
    CBP_DB_PATH,
    CHAT_API_KEY,
    CHAT_BASE_URL,
    CHAT_MODEL,
    CHAT_TIMEOUT_SECONDS,
    EMBEDDING_API_KEY,
    EMBEDDING_BASE_URL,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_MODEL,
    EMBEDDING_TIMEOUT_SECONDS,
    HTS_JSON_URL,
    HTS_VERSION,
    RAG_CHUNK_CHARS,
    RAG_CHUNK_OVERLAP,
    RAG_EVIDENCE_TOP_K,
    RAG_EXCERPT_CHARS,
    RAG_INDEX_PATH,
    RAG_KEYWORD_TOP_K,
    RAG_RERANK_TOP_K,
    RAG_VECTOR_TOP_K,
    RERANKER_API_KEY,
    RERANKER_BASE_URL,
    RERANKER_MODEL,
    RERANKER_TIMEOUT_SECONDS,
)
from app.errors import BadRequestError, ServiceUnavailableError, UpstreamError
from app.legal_knowledge import (
    chunk_legal_pages,
    default_legal_sources,
    extract_pdf_pages,
    read_source_bytes,
)

_SECTION_RE = re.compile(
    r"(?im)^\s*(FACTS|ISSUE(?:S)?|LAW AND ANALYSIS|ANALYSIS|HOLDING|BACKGROUND)\s*:?\s*$"
)
_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.-]{1,}")
_DISCLAIMER = (
    "本结果仅用于案例研究和初步归类辅助，不构成美国海关与边境保护局的"
    "正式约束性裁定。"
)


def _text_list(value: Any) -> list[str]:
    """Normalize an LLM string-or-array field without splitting strings."""
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list):
        values = value
    else:
        return []
    return [str(item).strip() for item in values if str(item).strip()]


def normalize_hts(value: str) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def _hash(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()


def _decode_json_text(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("model response must be a JSON object")
    return value


def chunk_ruling(text: str, max_chars: int = RAG_CHUNK_CHARS) -> list[dict[str, Any]]:
    """Split a ruling around legal section headers, then by bounded character windows."""
    clean = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not clean:
        return []

    matches = list(_SECTION_RE.finditer(clean))
    sections: list[tuple[str, int, str]] = []
    if not matches:
        sections.append(("BODY", 0, clean))
    else:
        if matches[0].start() > 0:
            sections.append(("HEADER", 0, clean[: matches[0].start()].strip()))
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(clean)
            sections.append((match.group(1).upper(), start, clean[start:end].strip()))

    result: list[dict[str, Any]] = []
    for section, base_start, body in sections:
        if not body:
            continue
        position = 0
        while position < len(body):
            end = min(len(body), position + max_chars)
            if end < len(body):
                boundary = body.rfind("\n\n", position, end)
                if boundary > position + max_chars // 2:
                    end = boundary
            piece = body[position:end].strip()
            if piece:
                result.append(
                    {
                        "section": section,
                        "text": piece,
                        "source_start": base_start + position,
                        "source_end": base_start + end,
                    }
                )
            if end >= len(body):
                break
            position = max(position + 1, end - RAG_CHUNK_OVERLAP)
    return result


class OpenAICompatibleClient:
    def __init__(
        self,
        chat_base_url: str = CHAT_BASE_URL,
        chat_api_key: str = CHAT_API_KEY,
        chat_model: str = CHAT_MODEL,
        chat_timeout: int = CHAT_TIMEOUT_SECONDS,
        embedding_base_url: str = EMBEDDING_BASE_URL,
        embedding_api_key: str = EMBEDDING_API_KEY,
        embedding_model: str = EMBEDDING_MODEL,
        embedding_timeout: int = EMBEDDING_TIMEOUT_SECONDS,
        reranker_base_url: str = RERANKER_BASE_URL,
        reranker_api_key: str = RERANKER_API_KEY,
        reranker_model: str = RERANKER_MODEL,
        reranker_timeout: int = RERANKER_TIMEOUT_SECONDS,
    ) -> None:
        self.chat_base_url = chat_base_url
        self.chat_api_key = chat_api_key
        self.chat_model = chat_model
        self.chat_timeout = chat_timeout
        self.embedding_base_url = embedding_base_url
        self.embedding_api_key = embedding_api_key
        self.embedding_model = embedding_model
        self.embedding_timeout = embedding_timeout
        self.reranker_base_url = reranker_base_url
        self.reranker_api_key = reranker_api_key
        self.reranker_model = reranker_model
        self.reranker_timeout = reranker_timeout

    def configured(self) -> bool:
        return bool(
            self.chat_api_key
            and self.chat_model
            and self.embedding_api_key
            and self.embedding_model
            and self.reranker_base_url
            and self.reranker_api_key
            and self.reranker_model
        )

    @staticmethod
    def _post(
        base_url: str,
        api_key: str,
        timeout: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if not api_key:
            raise ServiceUnavailableError("Model API key is not configured")
        request = urllib.request.Request(
            base_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise UpstreamError(f"Model service request failed: {exc}") from exc

    def embeddings(self, texts: list[str]) -> list[np.ndarray]:
        if not self.embedding_model:
            raise ServiceUnavailableError("Embedding model is not configured")
        result: list[np.ndarray] = []
        pending = [
            texts[start : start + EMBEDDING_BATCH_SIZE]
            for start in range(0, len(texts), EMBEDDING_BATCH_SIZE)
        ]
        while pending:
            batch = pending.pop(0)
            try:
                body = self._post(
                    self.embedding_base_url,
                    self.embedding_api_key,
                    self.embedding_timeout,
                    {"model": self.embedding_model, "input": batch},
                )
            except http.client.IncompleteRead as exc:
                if len(batch) == 1:
                    raise UpstreamError("Embedding response was truncated") from exc
                retry = []
                for item in [batch, *pending]:
                    if len(item) >= len(batch):
                        middle = len(item) // 2
                        retry.extend([item[:middle], item[middle:]])
                    else:
                        retry.append(item)
                pending = retry
                continue
            rows = sorted(body.get("data", []), key=lambda item: item.get("index", 0))
            if len(rows) != len(batch):
                raise UpstreamError("Embedding service returned an unexpected vector count")
            for row in rows:
                vector = np.asarray(row["embedding"], dtype=np.float32)
                norm = float(np.linalg.norm(vector))
                result.append(vector / norm if norm else vector)
        return result

    def rerank(
        self, query: str, documents: list[str], top_n: int
    ) -> list[dict[str, Any]]:
        if not (
            self.reranker_base_url
            and self.reranker_api_key
            and self.reranker_model
        ):
            raise ServiceUnavailableError("Reranker model is not configured")
        if not documents:
            return []
        body = self._post(
            self.reranker_base_url,
            self.reranker_api_key,
            self.reranker_timeout,
            {
                "model": self.reranker_model,
                "query": query,
                "documents": documents,
                "top_n": min(max(1, top_n), len(documents)),
                "return_documents": False,
            },
        )
        ranked: list[dict[str, Any]] = []
        seen: set[int] = set()
        for item in body.get("results", []):
            try:
                index = int(item["index"])
                score = float(item["relevance_score"])
            except (KeyError, TypeError, ValueError):
                continue
            if 0 <= index < len(documents) and index not in seen:
                seen.add(index)
                ranked.append({"index": index, "relevance_score": score})
        if not ranked:
            raise UpstreamError("Reranker did not return valid results")
        return ranked
    def chat_json(self, system: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.chat_model:
            raise ServiceUnavailableError("Chat model is not configured")
        body = self._post(
            self.chat_base_url,
            self.chat_api_key,
            self.chat_timeout,
            {
                "model": self.chat_model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {
                        "role": "user",
                        "content": json.dumps(payload, ensure_ascii=False),
                    },
                ],
            },
        )
        try:
            return _decode_json_text(body["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise UpstreamError("Model did not return valid JSON") from exc

class RagIndex:
    def __init__(
        self,
        index_path: str = RAG_INDEX_PATH,
        source_path: str = CBP_DB_PATH,
        client: OpenAICompatibleClient | None = None,
    ) -> None:
        self.index_path = index_path
        self.source_path = source_path
        self.client = client or OpenAICompatibleClient()

    def connect(self) -> sqlite3.Connection:
        Path(self.index_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.index_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY,
                    ruling_no TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    section TEXT NOT NULL,
                    text TEXT NOT NULL,
                    hs_codes TEXT NOT NULL,
                    year INTEGER,
                    ruling_date TEXT,
                    status TEXT NOT NULL,
                    detail_url TEXT NOT NULL,
                    source_start INTEGER NOT NULL,
                    source_end INTEGER NOT NULL,
                    embedding BLOB,
                    embedding_dim INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_chunks_ruling ON chunks(ruling_no);
                CREATE TABLE IF NOT EXISTS ruling_versions (
                    ruling_no TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    updated_at TEXT,
                    embedding_model TEXT NOT NULL
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(subject, text);
                CREATE TABLE IF NOT EXISTS hts_entries (
                    code_digits TEXT PRIMARY KEY,
                    code TEXT NOT NULL,
                    indent INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    parent_path TEXT NOT NULL,
                    general_rate TEXT NOT NULL,
                    special_rate TEXT NOT NULL,
                    other_rate TEXT NOT NULL,
                    version TEXT NOT NULL
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS hts_entries_fts USING fts5(
                    code_digits UNINDEXED, code, description, parent_path
                );
                CREATE TABLE IF NOT EXISTS legal_sources (
                    source_id TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    title TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    version TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS legal_chunks (
                    id INTEGER PRIMARY KEY,
                    chunk_id TEXT NOT NULL UNIQUE,
                    source_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    page INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    version TEXT NOT NULL,
                    content_hash TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_legal_scope ON legal_chunks(scope);
                CREATE INDEX IF NOT EXISTS idx_legal_source ON legal_chunks(source_id);
                CREATE VIRTUAL TABLE IF NOT EXISTS legal_chunks_fts USING fts5(
                    title, text, scope
                );
                CREATE TABLE IF NOT EXISTS index_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )
            hts_count = conn.execute("SELECT COUNT(*) FROM hts_entries").fetchone()[0]
            hts_fts_count = conn.execute("SELECT COUNT(*) FROM hts_entries_fts").fetchone()[0]
            if hts_count and not hts_fts_count:
                conn.execute(
                    """
                    INSERT INTO hts_entries_fts(code_digits, code, description, parent_path)
                    SELECT code_digits, code, description, parent_path FROM hts_entries
                    """
                )

    def status(self) -> dict[str, Any]:
        if not Path(self.index_path).is_file():
            return {
                "ready": False,
                "chunks": 0,
                "rulings": 0,
                "hts_entries": 0,
                "hts_version": "",
                "legal_chunks": 0,
            }
        self.init_schema()
        with self.connect() as conn:
            chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            rulings = conn.execute(
                "SELECT COUNT(DISTINCT ruling_no) FROM chunks"
            ).fetchone()[0]
            hts_entries = conn.execute("SELECT COUNT(*) FROM hts_entries").fetchone()[0]
            legal_chunks = conn.execute("SELECT COUNT(*) FROM legal_chunks").fetchone()[0]
            row = conn.execute(
                "SELECT value FROM index_meta WHERE key='hts_version'"
            ).fetchone()
        return {
            "ready": bool(chunks and hts_entries),
            "chunks": chunks,
            "rulings": rulings,
            "hts_entries": hts_entries,
            "hts_version": row[0] if row else "",
            "legal_chunks": legal_chunks,
        }

    def sync_rulings(self) -> dict[str, int]:
        self.init_schema()
        if not self.client.embedding_api_key or not self.client.embedding_model:
            raise ServiceUnavailableError("生成案例索引前请配置模型 API Key 和 Embedding 模型")

        source = sqlite3.connect(f"file:{self.source_path}?mode=ro", uri=True)
        source.row_factory = sqlite3.Row
        rows = source.execute(
            """
            SELECT ruling_no, subject, description, hs_code, hs_codes, year,
                   ruling_date, status, detail_url, updated_at
            FROM rulings WHERE description IS NOT NULL AND description != ''
            """
        ).fetchall()
        source.close()

        with self.connect() as conn:
            versions = {
                row["ruling_no"]: (row["content_hash"], row["embedding_model"])
                for row in conn.execute(
                    "SELECT ruling_no, content_hash, embedding_model FROM ruling_versions"
                )
            }

        changed: list[tuple[sqlite3.Row, str, list[dict[str, Any]]]] = []
        chunk_specs: list[tuple[sqlite3.Row, dict[str, Any]]] = []
        for row in rows:
            content_hash = _hash(
                row["subject"] or "",
                row["description"] or "",
                row["hs_codes"] or "",
                row["status"] or "",
            )
            if versions.get(row["ruling_no"]) == (
                content_hash,
                self.client.embedding_model,
            ):
                continue
            chunks = chunk_ruling(row["description"])
            changed.append((row, content_hash, chunks))
            chunk_specs.extend((row, chunk) for chunk in chunks)

        if not changed:
            return {"changed_rulings": 0, "written_chunks": 0}

        embed_texts = [
            f"{row['subject']}\n{chunk['section']}\n{chunk['text']}"
            for row, chunk in chunk_specs
        ]
        embeddings = self.client.embeddings(embed_texts)

        with self.connect() as conn:
            embedding_pos = 0
            for row, content_hash, chunks in changed:
                old_ids = [
                    item[0]
                    for item in conn.execute(
                        "SELECT id FROM chunks WHERE ruling_no=?", (row["ruling_no"],)
                    )
                ]
                conn.executemany(
                    "DELETE FROM chunks_fts WHERE rowid=?", [(item,) for item in old_ids]
                )
                conn.execute("DELETE FROM chunks WHERE ruling_no=?", (row["ruling_no"],))

                hs_codes = row["hs_codes"] or "[]"
                if hs_codes == "[]" and row["hs_code"]:
                    hs_codes = json.dumps([row["hs_code"]])
                for chunk in chunks:
                    vector = embeddings[embedding_pos]
                    embedding_pos += 1
                    cursor = conn.execute(
                        """
                        INSERT INTO chunks (
                            ruling_no, subject, section, text, hs_codes, year,
                            ruling_date, status, detail_url, source_start, source_end,
                            embedding, embedding_dim
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            row["ruling_no"],
                            row["subject"] or "",
                            chunk["section"],
                            chunk["text"],
                            hs_codes,
                            row["year"],
                            row["ruling_date"] or "",
                            row["status"] or "active",
                            row["detail_url"] or "",
                            chunk["source_start"],
                            chunk["source_end"],
                            vector.tobytes(),
                            int(vector.size),
                        ),
                    )
                    conn.execute(
                        "INSERT INTO chunks_fts(rowid, subject, text) VALUES (?, ?, ?)",
                        (cursor.lastrowid, row["subject"] or "", chunk["text"]),
                    )
                conn.execute(
                    """
                    INSERT INTO ruling_versions(ruling_no, content_hash, updated_at, embedding_model)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(ruling_no) DO UPDATE SET
                        content_hash=excluded.content_hash,
                        updated_at=excluded.updated_at,
                        embedding_model=excluded.embedding_model
                    """,
                    (
                        row["ruling_no"],
                        content_hash,
                        row["updated_at"],
                        self.client.embedding_model,
                    ),
                )
        return {
            "changed_rulings": len(changed),
            "written_chunks": len(chunk_specs),
        }

    def sync_hts(self, source: str = HTS_JSON_URL) -> dict[str, int | str]:
        self.init_schema()
        if re.match(r"^https?://", source):
            request = urllib.request.Request(
                source, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json,text/plain,*/*"}
            )
            try:
                with urllib.request.urlopen(
                    request, timeout=max(CHAT_TIMEOUT_SECONDS, EMBEDDING_TIMEOUT_SECONDS)
                ) as response:
                    payload = response.read()
            except urllib.error.HTTPError as exc:
                result = subprocess.run(
                    ["curl.exe", "-fsSL", source],
                    capture_output=True,
                    timeout=max(CHAT_TIMEOUT_SECONDS, EMBEDDING_TIMEOUT_SECONDS),
                )
                if result.returncode != 0:
                    raise UpstreamError(f"USITC HTS 下载失败: {exc}") from exc
                payload = result.stdout
            except (urllib.error.URLError, TimeoutError) as exc:
                raise UpstreamError(f"USITC HTS 下载失败: {exc}") from exc
            try:
                items = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise UpstreamError(f"USITC HTS JSON 解析失败: {exc}") from exc
        else:
            payload = Path(source).read_bytes()
            try:
                items = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise BadRequestError(f"HTS JSON 解析失败: {exc}") from exc
        if not isinstance(items, list):
            raise BadRequestError("HTS JSON 顶层必须为数组")
        payload_hash = hashlib.sha256(payload).hexdigest()
        with self.connect() as conn:
            previous_hash = conn.execute(
                "SELECT value FROM index_meta WHERE key='hts_content_hash'"
            ).fetchone()
            if previous_hash and previous_hash[0] == payload_hash:
                count = conn.execute("SELECT COUNT(*) FROM hts_entries").fetchone()[0]
                return {
                    "hts_entries": count,
                    "hts_version": HTS_VERSION,
                    "changed_entries": 0,
                    "deleted_entries": 0,
                    "unchanged": True,
                }

        stack: dict[int, str] = {}
        entries: list[tuple[Any, ...]] = []
        for item in items:
            description = str(item.get("description") or "").strip()
            indent = int(item.get("indent") or 0)
            for level in [level for level in stack if level >= indent]:
                del stack[level]
            path = " > ".join(stack[level] for level in sorted(stack))
            code = str(item.get("htsno") or "").strip()
            if code:
                digits = normalize_hts(code)
                entries.append(
                    (
                        digits,
                        code,
                        indent,
                        description,
                        path,
                        str(item.get("general") or ""),
                        str(item.get("special") or ""),
                        str(item.get("other") or ""),
                        HTS_VERSION,
                    )
                )
            if description:
                stack[indent] = description

        with self.connect() as conn:
            columns = (
                "code_digits", "code", "indent", "description", "parent_path",
                "general_rate", "special_rate", "other_rate", "version",
            )
            existing = {
                row["code_digits"]: tuple(row[column] for column in columns)
                for row in conn.execute("SELECT * FROM hts_entries")
            }
            incoming = {item[0]: item for item in entries}
            changed = [
                item for code, item in incoming.items()
                if existing.get(code) != item
            ]
            deleted = sorted(set(existing) - set(incoming))
            affected = [*deleted, *(item[0] for item in changed)]
            conn.executemany(
                "DELETE FROM hts_entries_fts WHERE code_digits=?",
                [(code,) for code in affected],
            )
            conn.executemany(
                "DELETE FROM hts_entries WHERE code_digits=?",
                [(code,) for code in deleted],
            )
            conn.executemany(
                """
                INSERT INTO hts_entries(
                    code_digits, code, indent, description, parent_path,
                    general_rate, special_rate, other_rate, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(code_digits) DO UPDATE SET
                    code=excluded.code, indent=excluded.indent,
                    description=excluded.description,
                    parent_path=excluded.parent_path,
                    general_rate=excluded.general_rate,
                    special_rate=excluded.special_rate,
                    other_rate=excluded.other_rate,
                    version=excluded.version
                """,
                changed,
            )
            conn.executemany(
                """
                INSERT INTO hts_entries_fts(code_digits, code, description, parent_path)
                VALUES (?, ?, ?, ?)
                """,
                [(item[0], item[1], item[3], item[4]) for item in changed],
            )
            conn.execute(
                """
                INSERT INTO index_meta(key, value) VALUES ('hts_version', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (HTS_VERSION,),
            )
            conn.execute(
                """
                INSERT INTO index_meta(key, value) VALUES ('hts_content_hash', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (payload_hash,),
            )
        return {
            "hts_entries": len(entries),
            "hts_version": HTS_VERSION,
            "changed_entries": len(changed),
            "deleted_entries": len(deleted),
            "unchanged": False,
        }

    @staticmethod
    def _fts_query(query: str) -> str:
        tokens = []
        for token in _WORD_RE.findall(query):
            clean = token.strip(".-")
            if len(clean) >= 3 and clean.lower() not in {"the", "and", "for", "with"}:
                tokens.append(f'"{clean.replace(chr(34), "")}"')
        return " OR ".join(dict.fromkeys(tokens[:24]))

    def retrieve(self, query: str, query_vector: np.ndarray) -> list[dict[str, Any]]:
        fts_query = self._fts_query(query)
        keyword_ids: list[int] = []
        with self.connect() as conn:
            if fts_query:
                keyword_ids = [
                    row[0]
                    for row in conn.execute(
                        """
                        SELECT rowid FROM chunks_fts
                        WHERE chunks_fts MATCH ?
                        ORDER BY bm25(chunks_fts) LIMIT ?
                        """,
                        (fts_query, RAG_KEYWORD_TOP_K),
                    )
                ]
            vector_rows = conn.execute(
                "SELECT id, embedding, embedding_dim FROM chunks WHERE embedding IS NOT NULL"
            ).fetchall()

            vector_ids: list[int] = []
            if vector_rows:
                compatible = [
                    row for row in vector_rows if row["embedding_dim"] == query_vector.size
                ]
                if compatible:
                    matrix = np.vstack(
                        [np.frombuffer(row["embedding"], dtype=np.float32) for row in compatible]
                    )
                    scores = matrix @ query_vector
                    top = np.argsort(scores)[::-1][:RAG_VECTOR_TOP_K]
                    vector_ids = [compatible[int(pos)]["id"] for pos in top]

            rrf: dict[int, float] = {}
            for rank, chunk_id in enumerate(keyword_ids, 1):
                rrf[chunk_id] = rrf.get(chunk_id, 0.0) + 1.0 / (60 + rank)
            for rank, chunk_id in enumerate(vector_ids, 1):
                rrf[chunk_id] = rrf.get(chunk_id, 0.0) + 1.0 / (60 + rank)
            if not rrf:
                return []

            placeholders = ",".join("?" for _ in rrf)
            rows = conn.execute(
                f"SELECT * FROM chunks WHERE id IN ({placeholders})", list(rrf)
            ).fetchall()

        cases: dict[str, dict[str, Any]] = {}
        for row in rows:
            item = dict(row)
            score = rrf[item["id"]]
            if item["status"] == "active":
                score += 0.002
            current = cases.get(item["ruling_no"])
            if current is None or score > current["score"]:
                item.pop("embedding", None)
                item["score"] = score
                try:
                    item["hs_codes"] = json.loads(item["hs_codes"] or "[]")
                except json.JSONDecodeError:
                    item["hs_codes"] = []
                cases[item["ruling_no"]] = item
        return sorted(cases.values(), key=lambda item: item["score"], reverse=True)[
            :RAG_RERANK_TOP_K
        ]

    def hts_candidates(
        self, cases: Iterable[dict[str, Any]], query: str = ""
    ) -> list[dict[str, Any]]:
        """Union case-derived codes with complete-HTS full-text heading matches."""
        prefixes: list[str] = []
        for case in cases:
            for code in case.get("hs_codes", []):
                digits = normalize_hts(code)
                if len(digits) >= 4:
                    prefixes.append(digits)
        prefixes.extend(
            item["code_digits"] for item in self.retrieve_hts_headings(query, 12)
        )
        with self.connect() as conn:
            found: dict[str, dict[str, Any]] = {}
            for digits in dict.fromkeys(prefixes):
                row = conn.execute(
                    "SELECT * FROM hts_entries WHERE code_digits=?", (digits,)
                ).fetchone()
                if row and len(row["code_digits"]) == 10:
                    found[row["code_digits"]] = dict(row)
                prefix_length = 6 if len(digits) >= 6 else 4
                for child in conn.execute(
                    """
                    SELECT * FROM hts_entries
                    WHERE code_digits LIKE ? AND length(code_digits)=10
                    LIMIT 12
                    """,
                    (f"{digits[:prefix_length]}%",),
                ):
                    found[child["code_digits"]] = dict(child)
                if len(found) >= 40:
                    break
        return list(found.values())[:40]

    def sync_legal(
        self, sources: list[dict[str, str]] | None = None
    ) -> dict[str, Any]:
        """Incrementally index official PDF text while preserving page citations."""
        self.init_schema()
        sources = sources or default_legal_sources()
        changed = 0
        unchanged = 0
        written_chunks = 0
        failures: list[dict[str, str]] = []
        with self.connect() as conn:
            known = {
                row["source_id"]: row["content_hash"]
                for row in conn.execute("SELECT source_id, content_hash FROM legal_sources")
            }
        for source in sources:
            try:
                payload = read_source_bytes(source["url"])
                document_hash = hashlib.sha256(payload + b"\0legal-parser-v2").hexdigest()
                if known.get(source["source_id"]) == document_hash:
                    unchanged += 1
                    continue
                chunks = chunk_legal_pages(
                    extract_pdf_pages(payload), source, HTS_VERSION, RAG_CHUNK_CHARS
                )
                with self.connect() as conn:
                    old_ids = [
                        row[0] for row in conn.execute(
                            "SELECT id FROM legal_chunks WHERE source_id=? AND version=?",
                            (source["source_id"], HTS_VERSION),
                        )
                    ]
                    conn.executemany(
                        "DELETE FROM legal_chunks_fts WHERE rowid=?",
                        [(row_id,) for row_id in old_ids],
                    )
                    conn.execute(
                        "DELETE FROM legal_chunks WHERE source_id=? AND version=?",
                        (source["source_id"], HTS_VERSION),
                    )
                    for chunk in chunks:
                        cursor = conn.execute(
                            """
                            INSERT INTO legal_chunks(
                                chunk_id, source_id, source_type, title, scope, page,
                                text, source_url, version, content_hash
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                chunk["chunk_id"], chunk["source_id"],
                                chunk["source_type"], chunk["title"], chunk["scope"],
                                chunk["page"], chunk["text"], chunk["source_url"],
                                chunk["version"], chunk["content_hash"],
                            ),
                        )
                        conn.execute(
                            "INSERT INTO legal_chunks_fts(rowid, title, text, scope) VALUES (?, ?, ?, ?)",
                            (cursor.lastrowid, chunk["title"], chunk["text"], chunk["scope"]),
                        )
                    conn.execute(
                        """
                        INSERT INTO legal_sources(
                            source_id, content_hash, title, source_type, scope,
                            source_url, version
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(source_id) DO UPDATE SET
                            content_hash=excluded.content_hash,
                            title=excluded.title,
                            source_type=excluded.source_type,
                            scope=excluded.scope,
                            source_url=excluded.source_url,
                            version=excluded.version
                        """,
                        (
                            source["source_id"], document_hash, source["title"],
                            source["source_type"], source["scope"], source["url"],
                            HTS_VERSION,
                        ),
                    )
                changed += 1
                written_chunks += len(chunks)
            except (OSError, UpstreamError, KeyError) as exc:
                failures.append({
                    "source_id": str(source.get("source_id") or ""),
                    "error": str(exc),
                })
        return {
            "changed_sources": changed,
            "unchanged_sources": unchanged,
            "written_chunks": written_chunks,
            "failed_sources": failures,
        }

    def retrieve_hts_headings(
        self, query: str, limit: int = 12
    ) -> list[dict[str, Any]]:
        """Search the complete current HTS and aggregate matches to legal headings."""
        fts_query = self._fts_query(query)
        if not fts_query:
            return []
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT code_digits, bm25(hts_entries_fts) AS rank
                FROM hts_entries_fts
                WHERE hts_entries_fts MATCH ?
                ORDER BY rank LIMIT ?
                """,
                (fts_query, max(limit * 8, 40)),
            ).fetchall()
            headings: dict[str, dict[str, Any]] = {}
            for row in rows:
                prefix = row["code_digits"][:4]
                if len(prefix) != 4 or prefix in headings:
                    continue
                heading = conn.execute(
                    "SELECT * FROM hts_entries WHERE code_digits=? AND length(code_digits)=4",
                    (prefix,),
                ).fetchone()
                if heading:
                    item = dict(heading)
                    item["search_rank"] = float(row["rank"])
                    headings[prefix] = item
                if len(headings) >= limit:
                    break
        return list(headings.values())

    def retrieve_legal(
        self, query: str, heading_codes: Iterable[str], limit: int = 16
    ) -> list[dict[str, Any]]:
        fts_query = self._fts_query(query)
        chapters = {
            normalize_hts(code)[:2] for code in heading_codes
            if len(normalize_hts(code)) >= 2
        }
        scopes = ["general", *(f"chapter:{chapter}" for chapter in sorted(chapters))]
        with self.connect() as conn:
            found: dict[int, dict[str, Any]] = {}
            general_rows = conn.execute(
                """
                SELECT * FROM legal_chunks
                WHERE version=? AND scope='general'
                ORDER BY CASE
                    WHEN upper(text) LIKE '%GENERAL RULES OF INTERPRETATION%' THEN 0
                    WHEN upper(title) LIKE '%TARIFF CLASSIFICATION%' THEN 1
                    ELSE 2 END, page
                LIMIT 6
                """,
                (HTS_VERSION,),
            ).fetchall()
            for row in general_rows:
                found[row["id"]] = dict(row)
            if fts_query:
                placeholders = ",".join("?" for _ in scopes)
                rows = conn.execute(
                    f"""
                    SELECT legal_chunks.*, bm25(legal_chunks_fts) AS rank
                    FROM legal_chunks_fts
                    JOIN legal_chunks ON legal_chunks.id=legal_chunks_fts.rowid
                    WHERE legal_chunks_fts MATCH ?
                      AND legal_chunks.version=?
                      AND legal_chunks.scope IN ({placeholders})
                    ORDER BY rank LIMIT ?
                    """,
                    (fts_query, HTS_VERSION, *scopes, limit),
                ).fetchall()
                for row in rows:
                    found[row["id"]] = dict(row)
        return list(found.values())[:limit]

    def hts_hierarchy(self, code: str) -> list[dict[str, Any]]:
        digits = normalize_hts(code)
        if len(digits) != 10:
            return []
        prefixes = [digits[:4], digits[:6], digits[:8], digits]
        with self.connect() as conn:
            rows = {
                row["code_digits"]: dict(row)
                for row in conn.execute(
                    "SELECT * FROM hts_entries WHERE code_digits IN (?, ?, ?, ?)",
                    prefixes,
                )
            }
        return [rows[prefix] for prefix in prefixes if prefix in rows]

    def hts_entry(self, code: str) -> dict[str, Any] | None:
        digits = normalize_hts(code)
        if len(digits) not in {4, 6, 8, 10}:
            return None
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM hts_entries WHERE code_digits=?", (digits,)
            ).fetchone()
        return dict(row) if row else None

    def exact_hts(self, code: str) -> dict[str, Any] | None:
        digits = normalize_hts(code)
        if len(digits) != 10:
            return None
        return self.hts_entry(digits)


class ClassificationService:
    def __init__(
        self,
        index: RagIndex | None = None,
        client: OpenAICompatibleClient | None = None,
    ) -> None:
        self.client = client or OpenAICompatibleClient()
        self.index = index or RagIndex(client=self.client)

    def classify(self, product: dict[str, Any]) -> dict[str, Any]:
        status = self.index.status()
        if not status["ready"]:
            raise ServiceUnavailableError(
                "知识库尚未就绪，请先运行 python -m app.rag sync"
            )
        if not self.client.configured():
            raise ServiceUnavailableError(
                "请在 backend/config.json 中完整配置 chat、embedding 和 reranker 模型"
            )
        profile = self.client.chat_json(
            (
                "You convert a Chinese or English product description into an English "
                "HTSUS and CBP ruling retrieval query. Use only supplied facts. Return JSON "
                "with english_query (string), keywords (array), and missing_information "
                "(array). Retrieval text must be English; missing information must be "
                "Simplified Chinese."
            ),
            product,
        )
        english_query = str(profile.get("english_query") or "").strip()
        if not english_query:
            raise UpstreamError("模型未生成可检索的英文商品描述")
        query_vector = self.client.embeddings([english_query])[0]
        cases = self.index.retrieve(english_query, query_vector)
        selected_cases: list[dict[str, Any]] = []
        selected_compact: list[dict[str, Any]] = []
        selected_meta: dict[str, dict[str, Any]] = {}
        if cases:
            compact_cases = [
                {
                    "ruling_no": case["ruling_no"],
                    "subject": case["subject"],
                    "year": case["year"],
                    "status": case["status"],
                    "hs_codes": case["hs_codes"],
                    "evidence": case["text"][:RAG_EXCERPT_CHARS],
                }
                for case in cases
            ]
            rerank_documents = [
                (
                    f"Ruling: {case['ruling_no']}\nSubject: {case['subject']}\n"
                    f"Year: {case['year']}\nStatus: {case['status']}\n"
                    f"HTS codes: {', '.join(case['hs_codes'])}\n"
                    f"Evidence: {case['text'][:RAG_EXCERPT_CHARS]}"
                )
                for case in cases
            ]
            ranked = self.client.rerank(
                english_query, rerank_documents, RAG_EVIDENCE_TOP_K
            )
            selected_cases = [cases[item["index"]] for item in ranked]
            selected_compact = [compact_cases[item["index"]] for item in ranked]
            selected_meta = {
                cases[item["index"]]["ruling_no"]: {
                    "rerank_score": item["relevance_score"]
                }
                for item in ranked
            }

        hts_headings = self.index.retrieve_hts_headings(english_query, 12)
        hts_candidates = self.index.hts_candidates(selected_cases, english_query)
        if not hts_candidates:
            return self._insufficient(
                profile, "完整 HTS 文本与历史案例均未召回可验证的现行十位税号"
            )
        legal_chunks = self.index.retrieve_legal(
            english_query,
            [item["code_digits"] for item in hts_headings],
        )
        legal_payload = [
            {
                "evidence_id": f"legal:{item['chunk_id']}",
                "title": item["title"],
                "scope": item["scope"],
                "page": item["page"],
                "text": item["text"][:RAG_EXCERPT_CHARS],
            }
            for item in legal_chunks
        ]

        decision = self.client.chat_json(
            (
                "Act as a cautious HTSUS classification research assistant. Choose only "
                "from current_hts and compare the supplied four-digit headings under GRI 1 "
                "before applying only relevant later rules. Use legal_evidence and CBP cases "
                "as support; never invent codes or evidence ids. Return JSON with "
                "primary_hts_code, confidence (high|medium|low), basis, alternative_codes "
                "(at most 3), used_ruling_numbers, missing_information, reference_analysis, "
                "rules_applied (objects: rule, reason, evidence_ids), and heading_analysis "
                "(objects: heading_code, status selected|excluded|pending, reason, "
                "evidence_ids, ruling_numbers). All explanations must be Simplified Chinese. "
                "Keep official English descriptions and quotations unchanged."
            ),
            {
                "product": product,
                "profile": profile,
                "cases": selected_compact,
                "candidate_headings": [
                    {
                        "hts_code": item["code"],
                        "description": item["description"],
                        "parent_path": item["parent_path"],
                    }
                    for item in hts_headings
                ],
                "current_hts": [
                    {
                        "hts_code": item["code"],
                        "description": item["description"],
                        "parent_path": item["parent_path"],
                    }
                    for item in hts_candidates
                ],
                "legal_evidence": legal_payload,
                "hts_version": status["hts_version"],
            },
        )
        reference_analysis = decision.get("reference_analysis", [])
        if isinstance(reference_analysis, dict):
            reference_analysis = [reference_analysis]
        if not isinstance(reference_analysis, list):
            reference_analysis = []
        for item in reference_analysis:
            if not isinstance(item, dict):
                continue
            ruling_no = str(item.get("ruling_no") or "")
            if ruling_no in selected_meta:
                selected_meta[ruling_no]["similarities"] = _text_list(
                    item.get("similarities")
                )
                selected_meta[ruling_no]["differences"] = _text_list(
                    item.get("differences")
                )
        return self._validated_result(
            decision, profile, selected_cases, selected_meta, status, hts_candidates,
            legal_chunks, hts_headings, product,
        )

    def _validated_result(
        self,
        decision: dict[str, Any],
        profile: dict[str, Any],
        cases: list[dict[str, Any]],
        selected_meta: dict[str, dict[str, Any]],
        status: dict[str, Any],
        hts_candidates: list[dict[str, Any]],
        legal_chunks: list[dict[str, Any]] | None = None,
        hts_headings: list[dict[str, Any]] | None = None,
        product: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        legal_chunks = legal_chunks or []
        hts_headings = hts_headings or []
        product = product or {}
        allowed = {case["ruling_no"]: case for case in cases}
        used = [
            item for item in _text_list(decision.get("used_ruling_numbers"))
            if item in allowed
        ]
        if not used:
            used = list(allowed)[: min(3, len(allowed))]

        allowed_hts = {item["code_digits"] for item in hts_candidates}
        primary_code = normalize_hts(str(decision.get("primary_hts_code") or ""))
        primary_row = (
            self.index.exact_hts(primary_code) if primary_code in allowed_hts else None
        )
        warnings: list[str] = []
        primary = None
        if primary_row:
            primary = {
                "hts_code": primary_row["code"],
                "description": primary_row["description"],
                "parent_path": primary_row.get("parent_path", ""),
                "confidence": (
                    decision.get("confidence")
                    if decision.get("confidence") in {"high", "medium", "low"}
                    else "low"
                ),
                "basis": _text_list(decision.get("basis")),
            }
        else:
            warnings.append("模型候选税号未通过当前 HTS 有效性校验，未给出主税号。")
        if not cases:
            warnings.append("未检索到足够相似的 CBP 案例，本次路径主要依据现行法律文本，置信度已降低。")
            if primary and primary["confidence"] == "high":
                primary["confidence"] = "medium"

        alternatives = []
        alternative_codes = decision.get("alternative_codes", [])
        if isinstance(alternative_codes, dict):
            alternative_codes = [alternative_codes]
        if not isinstance(alternative_codes, list):
            alternative_codes = []
        for item in alternative_codes[:3]:
            if not isinstance(item, dict):
                continue
            code = normalize_hts(str(item.get("hts_code") or ""))
            row = self.index.exact_hts(code) if code in allowed_hts else None
            if row:
                alternatives.append({
                    "hts_code": row["code"],
                    "description": row["description"],
                    "reason": str(item.get("reason") or ""),
                })

        references = []
        for ruling_no in used:
            case = allowed[ruling_no]
            meta = selected_meta.get(ruling_no, {})
            references.append({
                "ruling_no": ruling_no,
                "subject": case["subject"],
                "ruling_date": case["ruling_date"],
                "year": case["year"] or 0,
                "hs_codes": case["hs_codes"],
                "status": case["status"],
                "detail_url": case["detail_url"],
                "section": case["section"],
                "excerpt": case["text"][:RAG_EXCERPT_CHARS],
                "similarities": _text_list(meta.get("similarities")),
                "differences": _text_list(meta.get("differences")),
            })

        if references and not any(item["status"] == "active" for item in references):
            allowed_legal_ids = {
                f"legal:{item['chunk_id']}" for item in legal_chunks
            }
            rules = decision.get("rules_applied", [])
            if isinstance(rules, dict):
                rules = [rules]
            has_legal_support = any(
                evidence_id in allowed_legal_ids
                for rule in rules if isinstance(rule, dict)
                for evidence_id in _text_list(rule.get("evidence_ids"))
            )
            warnings.append("参考案例均为已撤销或已修改状态，不能作为唯一主依据。")
            if primary and not has_legal_support:
                primary = None
                warnings.append("缺少被实际引用的现行法律依据，已撤回主税号结论。")

        missing = list(dict.fromkeys(
            _text_list(profile.get("missing_information"))
            + _text_list(decision.get("missing_information"))
        ))
        tree = self._build_tree(
            decision, product, primary, alternatives, references, legal_chunks,
            hts_headings, hts_candidates, missing,
        )
        return {
            "product_profile": str(profile.get("english_query") or ""),
            "primary": primary,
            "alternatives": alternatives,
            "references": references,
            "missing_information": missing,
            "warnings": warnings,
            "hts_version": status["hts_version"],
            "disclaimer": _DISCLAIMER,
            "classification_tree": tree,
        }

    def _build_tree(
        self,
        decision: dict[str, Any],
        product: dict[str, Any],
        primary: dict[str, Any] | None,
        alternatives: list[dict[str, Any]],
        references: list[dict[str, Any]],
        legal_chunks: list[dict[str, Any]],
        hts_headings: list[dict[str, Any]],
        hts_candidates: list[dict[str, Any]],
        missing: list[str],
    ) -> dict[str, Any]:
        evidence: list[dict[str, Any]] = []
        facts = []
        labels = {
            "product_name": "产品名称", "product_type": "产品类型",
            "description": "完整产品描述", "materials": "材料",
            "components": "主要部件", "functions": "功能",
            "intended_use": "主要用途", "technical_specs": "技术规格",
            "country_of_origin": "原产国",
        }
        for key, label in labels.items():
            value = product.get(key)
            if isinstance(value, list):
                value = "、".join(str(item) for item in value if item)
            if value:
                facts.append(f"{label}：{value}")
        evidence.append({
            "id": "product:input", "type": "product_input", "title": "用户输入的商品事实",
            "excerpt": "\n".join(facts),
        })
        legal_by_id: dict[str, dict[str, Any]] = {}
        for item in legal_chunks:
            evidence_id = f"legal:{item['chunk_id']}"
            legal_by_id[evidence_id] = item
            evidence.append({
                "id": evidence_id,
                "type": "cbp_guide" if item["source_type"] == "cbp_guide" else "hts_legal",
                "title": item["title"], "excerpt": item["text"],
                "url": item["source_url"], "page": item["page"],
            })
        case_by_id: dict[str, dict[str, Any]] = {}
        for item in references:
            evidence_id = f"case:{item['ruling_no']}"
            case_by_id[evidence_id] = item
            evidence.append({
                "id": evidence_id, "type": "cbp_case", "title": item["subject"],
                "excerpt": item["excerpt"], "url": item["detail_url"],
                "ruling_no": item["ruling_no"], "status": item["status"],
            })

        rules = decision.get("rules_applied", [])
        if isinstance(rules, dict):
            rules = [rules]
        rule_nodes = []
        for index, item in enumerate(rules if isinstance(rules, list) else []):
            if not isinstance(item, dict):
                continue
            ids = [
                value for value in _text_list(item.get("evidence_ids"))
                if value in legal_by_id
            ]
            title = str(item.get("rule") or f"适用规则 {index + 1}")
            rule_nodes.append({
                "id": f"rule:{index + 1}",
                "node_type": "interpretation_rule" if "GRI" in title.upper() else "legal_note",
                "status": "selected",
                "title": title,
                "rationale": _text_list(item.get("reason")),
                "evidence_ids": ids,
                "children": [],
            })

        allowed_headings: dict[str, dict[str, Any]] = {}
        for row in [*hts_headings, *hts_candidates]:
            digits = normalize_hts(row.get("code_digits") or row.get("code") or "")
            prefix = digits[:4]
            if len(prefix) == 4 and prefix not in allowed_headings:
                heading = next(
                    (item for item in hts_headings if item.get("code_digits") == prefix),
                    None,
                )
                if not heading and hasattr(self.index, "hts_entry"):
                    heading = self.index.hts_entry(prefix)
                if heading:
                    allowed_headings[prefix] = heading
        analyses = decision.get("heading_analysis", [])
        if isinstance(analyses, dict):
            analyses = [analyses]
        analysis_by_heading: dict[str, dict[str, Any]] = {}
        for item in analyses if isinstance(analyses, list) else []:
            if not isinstance(item, dict):
                continue
            code = normalize_hts(str(item.get("heading_code") or ""))[:4]
            if code in allowed_headings:
                analysis_by_heading[code] = item
        primary_digits = normalize_hts(primary["hts_code"]) if primary else ""
        requested = list(analysis_by_heading)
        for code in [primary_digits[:4], *(
            normalize_hts(item["hts_code"])[:4] for item in alternatives
        )]:
            if code in allowed_headings and code not in requested:
                requested.append(code)
        if not requested:
            requested = list(allowed_headings)[:4]

        heading_nodes = []
        for heading_code in requested[:6]:
            row = allowed_headings[heading_code]
            analysis = analysis_by_heading.get(heading_code, {})
            selected = bool(primary_digits and heading_code == primary_digits[:4])
            model_status = str(analysis.get("status") or "")
            status = "selected" if selected else (
                "excluded" if model_status == "excluded" else "pending"
            )
            evidence_ids = [
                value for value in _text_list(analysis.get("evidence_ids"))
                if value in legal_by_id
            ]
            ruling_ids = [
                f"case:{value}" for value in _text_list(analysis.get("ruling_numbers"))
                if f"case:{value}" in case_by_id
            ]
            heading_evidence_id = f"hts:{heading_code}"
            evidence.append({
                "id": heading_evidence_id, "type": "hts_entry",
                "title": row.get("description") or "候选四位品目",
                "excerpt": row.get("parent_path") or "",
                "hts_code": row.get("code") or heading_code,
            })
            node = {
                "id": f"heading:{heading_code}", "node_type": "candidate_heading",
                "status": status, "title": row.get("description") or "候选四位品目",
                "hts_code": row.get("code") or heading_code,
                "rationale": _text_list(analysis.get("reason")),
                "evidence_ids": [heading_evidence_id, *evidence_ids], "children": [],
            }
            if selected and hasattr(self.index, "hts_hierarchy"):
                hierarchy = self.index.hts_hierarchy(primary_digits)
                if [len(item["code_digits"]) for item in hierarchy] == [4, 6, 8, 10]:
                    parent = node
                    for level in hierarchy[1:]:
                        hts_id = f"hts:{level['code_digits']}"
                        evidence.append({
                            "id": hts_id, "type": "hts_entry",
                            "title": level["description"], "excerpt": level.get("parent_path", ""),
                            "hts_code": level["code"],
                        })
                        child = {
                            "id": f"subheading:{level['code_digits']}",
                            "node_type": "subheading", "status": "selected",
                            "title": level["description"], "hts_code": level["code"],
                            "rationale": primary.get("basis", []) if len(level["code_digits"]) == 10 else [],
                            "evidence_ids": [hts_id], "children": [],
                        }
                        parent["children"].append(child)
                        parent = child
            for case_id in ruling_ids:
                case = case_by_id[case_id]
                node["children"].append({
                    "id": f"node:{case_id}", "node_type": "case", "status": status,
                    "title": f"{case['ruling_no']}：{case['subject']}",
                    "rationale": case["similarities"], "evidence_ids": [case_id],
                    "children": [],
                })
            heading_nodes.append(node)

        return {
            "root": {
                "id": "product", "node_type": "product_facts",
                "status": "pending" if missing or not primary else "selected",
                "title": str(product.get("product_name") or "待分类商品"),
                "rationale": facts, "missing_information": missing,
                "evidence_ids": ["product:input"],
                "children": [*rule_nodes, *heading_nodes],
            },
            "evidence": evidence,
        }

    @staticmethod
    def _insufficient(profile: dict[str, Any], warning: str) -> dict[str, Any]:
        return {
            "product_profile": str(profile.get("english_query") or ""),
            "primary": None, "alternatives": [], "references": [],
            "missing_information": _text_list(profile.get("missing_information")),
            "warnings": [warning], "hts_version": "",
            "disclaimer": _DISCLAIMER, "classification_tree": None,
        }


def sync_index() -> dict[str, Any]:
    index = RagIndex()
    return {
        "rulings": index.sync_rulings(),
        "hts": index.sync_hts(),
        "legal": index.sync_legal(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build/update the CBP RAG index")
    parser.add_argument("command", choices=["sync", "sync-legal", "status"])
    parser.add_argument("--hts-json", default=HTS_JSON_URL)
    args = parser.parse_args()
    index = RagIndex()
    if args.command == "status":
        print(json.dumps(index.status(), ensure_ascii=False, indent=2))
        return
    if args.command == "sync-legal":
        print(json.dumps(index.sync_legal(), ensure_ascii=False, indent=2))
        return
    result = {
        "rulings": index.sync_rulings(),
        "hts": index.sync_hts(args.hts_json),
        "legal": index.sync_legal(),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
