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

_SECTION_RE = re.compile(
    r"(?im)^\s*(FACTS|ISSUE(?:S)?|LAW AND ANALYSIS|ANALYSIS|HOLDING|BACKGROUND)\s*:?\s*$"
)
_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.-]{1,}")
_DISCLAIMER = (
    "本结果仅用于案例研究和初步归类辅助，不构成美国海关与边境保护局的"
    "正式约束性裁定。"
)


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
                CREATE TABLE IF NOT EXISTS index_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
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
            }
        with self.connect() as conn:
            chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            rulings = conn.execute(
                "SELECT COUNT(DISTINCT ruling_no) FROM chunks"
            ).fetchone()[0]
            hts_entries = conn.execute("SELECT COUNT(*) FROM hts_entries").fetchone()[0]
            row = conn.execute(
                "SELECT value FROM index_meta WHERE key='hts_version'"
            ).fetchone()
        return {
            "ready": bool(chunks and hts_entries),
            "chunks": chunks,
            "rulings": rulings,
            "hts_entries": hts_entries,
            "hts_version": row[0] if row else "",
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
            with open(source, "r", encoding="utf-8") as handle:
                items = json.load(handle)
        if not isinstance(items, list):
            raise BadRequestError("HTS JSON 顶层必须为数组")

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
            conn.execute("DELETE FROM hts_entries")
            conn.executemany(
                """
                INSERT OR REPLACE INTO hts_entries(
                    code_digits, code, indent, description, parent_path,
                    general_rate, special_rate, other_rate, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                entries,
            )
            conn.execute(
                """
                INSERT INTO index_meta(key, value) VALUES ('hts_version', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (HTS_VERSION,),
            )
        return {"hts_entries": len(entries), "hts_version": HTS_VERSION}

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

    def hts_candidates(self, cases: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        prefixes: list[str] = []
        for case in cases:
            for code in case.get("hs_codes", []):
                digits = normalize_hts(code)
                if len(digits) >= 6:
                    prefixes.append(digits)
        if not prefixes:
            return []
        with self.connect() as conn:
            found: dict[str, dict[str, Any]] = {}
            for digits in dict.fromkeys(prefixes):
                row = conn.execute(
                    "SELECT * FROM hts_entries WHERE code_digits=?", (digits,)
                ).fetchone()
                if row and len(row["code_digits"]) == 10:
                    found[row["code_digits"]] = dict(row)
                    continue
                for child in conn.execute(
                    """
                    SELECT * FROM hts_entries
                    WHERE code_digits LIKE ? AND length(code_digits)=10
                    LIMIT 12
                    """,
                    (f"{digits[:6]}%",),
                ):
                    found[child["code_digits"]] = dict(child)
        return list(found.values())[:40]

    def exact_hts(self, code: str) -> dict[str, Any] | None:
        digits = normalize_hts(code)
        if len(digits) != 10:
            return None
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM hts_entries WHERE code_digits=?", (digits,)
            ).fetchone()
        return dict(row) if row else None


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
                "CBP ruling retrieval query. Use only supplied facts. Return JSON with "
                "english_query (string), keywords (array), and missing_information (array). "
                "english_query and keywords must be English for retrieval; every item in "
                "missing_information must be written in Simplified Chinese."
            ),
            product,
        )
        english_query = str(profile.get("english_query") or "").strip()
        if not english_query:
            raise UpstreamError("模型未生成可检索的英文商品描述")
        query_vector = self.client.embeddings([english_query])[0]
        cases = self.index.retrieve(english_query, query_vector)
        if not cases:
            return self._insufficient(profile, "未检索到相关 CBP 裁定")

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
        hts_candidates = self.index.hts_candidates(selected_cases)
        if not hts_candidates:
            return self._insufficient(profile, "相关案例的历史税号无法映射到当前 HTS")

        decision = self.client.chat_json(
            (
                "Act as a cautious HTSUS classification research assistant. Choose only "
                "from current_hts. Use CBP cases as analogies, explain similarities and "
                "material differences, and do not claim a binding ruling. Return JSON with "
                "primary_hts_code (or empty if evidence is insufficient), confidence "
                "(high|medium|low), basis (array of concise strings), alternative_codes "
                "(array of at most 3 objects: hts_code, reason), used_ruling_numbers "
                "(array containing only supplied ruling numbers), missing_information, and "
                "reference_analysis (array of objects with ruling_no, similarities, and "
                "differences for each actually used ruling). All generated explanatory "
                "content must be in Simplified Chinese, including basis, alternative reason, "
                "missing_information, similarities, and differences. Keep ruling numbers, "
                "HTS codes, official HTS descriptions, and quoted CBP evidence unchanged."
            ),
            {
                "product": product,
                "profile": profile,
                "cases": selected_compact,
                "current_hts": [
                    {
                        "hts_code": item["code"],
                        "description": item["description"],
                        "parent_path": item["parent_path"],
                    }
                    for item in hts_candidates
                ],
                "hts_version": status["hts_version"],
            },
        )
        for item in decision.get("reference_analysis", []):
            ruling_no = str(item.get("ruling_no") or "")
            if ruling_no in selected_meta:
                selected_meta[ruling_no]["similarities"] = [
                    str(value) for value in item.get("similarities", [])
                ]
                selected_meta[ruling_no]["differences"] = [
                    str(value) for value in item.get("differences", [])
                ]
        return self._validated_result(
            decision, profile, selected_cases, selected_meta, status, hts_candidates
        )

    def _validated_result(
        self,
        decision: dict[str, Any],
        profile: dict[str, Any],
        cases: list[dict[str, Any]],
        selected_meta: dict[str, dict[str, Any]],
        status: dict[str, Any],
        hts_candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        allowed = {case["ruling_no"]: case for case in cases}
        used = [
            str(item)
            for item in decision.get("used_ruling_numbers", [])
            if str(item) in allowed
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
                "parent_path": primary_row["parent_path"],
                "confidence": (
                    decision.get("confidence")
                    if decision.get("confidence") in {"high", "medium", "low"}
                    else "low"
                ),
                "basis": [
                    str(item) for item in decision.get("basis", []) if str(item).strip()
                ],
            }
        else:
            warnings.append("模型候选税号未通过当前 HTS 有效性校验，未给出主税号。")

        alternatives = []
        for item in decision.get("alternative_codes", [])[:3]:
            code = normalize_hts(str(item.get("hts_code") or ""))
            row = self.index.exact_hts(code) if code in allowed_hts else None
            if row:
                alternatives.append(
                    {
                        "hts_code": row["code"],
                        "description": row["description"],
                        "reason": str(item.get("reason") or ""),
                    }
                )

        references = []
        for ruling_no in used:
            case = allowed[ruling_no]
            meta = selected_meta.get(ruling_no, {})
            references.append(
                {
                    "ruling_no": ruling_no,
                    "subject": case["subject"],
                    "ruling_date": case["ruling_date"],
                    "year": case["year"] or 0,
                    "hs_codes": case["hs_codes"],
                    "status": case["status"],
                    "detail_url": case["detail_url"],
                    "section": case["section"],
                    "excerpt": case["text"][:RAG_EXCERPT_CHARS],
                    "similarities": [
                        str(item) for item in meta.get("similarities", [])
                    ],
                    "differences": [
                        str(item) for item in meta.get("differences", [])
                    ],
                }
            )

        missing = list(
            dict.fromkeys(
                [
                    str(item)
                    for item in (
                        list(profile.get("missing_information", []))
                        + list(decision.get("missing_information", []))
                    )
                    if str(item).strip()
                ]
            )
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
        }

    @staticmethod
    def _insufficient(profile: dict[str, Any], warning: str) -> dict[str, Any]:
        return {
            "product_profile": str(profile.get("english_query") or ""),
            "primary": None,
            "alternatives": [],
            "references": [],
            "missing_information": [
                str(item) for item in profile.get("missing_information", [])
            ],
            "warnings": [warning],
            "hts_version": "",
            "disclaimer": _DISCLAIMER,
        }


def sync_index() -> dict[str, Any]:
    index = RagIndex()
    return {"rulings": index.sync_rulings(), "hts": index.sync_hts()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build/update the CBP RAG index")
    parser.add_argument("command", choices=["sync", "status"])
    parser.add_argument("--hts-json", default=HTS_JSON_URL)
    args = parser.parse_args()
    index = RagIndex()
    if args.command == "status":
        print(json.dumps(index.status(), ensure_ascii=False, indent=2))
        return
    result = {
        "rulings": index.sync_rulings(),
        "hts": index.sync_hts(args.hts_json),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
