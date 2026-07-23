import http.client
import json
import sqlite3

import numpy as np

from app.rag import (
    ClassificationService, OpenAICompatibleClient, RagIndex, _text_list, chunk_ruling,
)


class FakeEmbeddingClient:
    embedding_api_key = "test"
    embedding_model = "fake-embedding"

    def embeddings(self, texts):
        vectors = []
        for text in texts:
            vector = np.array(
                [len(text), text.lower().count("battery") + 1, 1],
                dtype=np.float32,
            )
            vectors.append(vector / np.linalg.norm(vector))
        return vectors


def _source_db(path):
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE rulings (
            ruling_no TEXT PRIMARY KEY, subject TEXT, description TEXT,
            hs_code TEXT, hs_codes TEXT, year INTEGER, ruling_date TEXT,
            status TEXT, detail_url TEXT, updated_at TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO rulings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "N10000",
            "Battery cable",
            "FACTS:\nA copper battery cable.\n\n"
            "HOLDING:\nThe cable is classified as 8544.42.9000.",
            "8544.42.9000",
            '["8544.42.9000"]',
            2025,
            "2025-01-01",
            "active",
            "https://rulings.cbp.gov/ruling/N10000",
            "2025-01-02",
        ),
    )
    conn.commit()
    conn.close()


def test_chunk_ruling_preserves_sections():
    chunks = chunk_ruling("Header text\n\nFACTS:\nA product.\n\nHOLDING:\n8544.42.9000")
    assert [chunk["section"] for chunk in chunks] == ["HEADER", "FACTS", "HOLDING"]
    assert "A product" in chunks[1]["text"]


def test_index_sync_is_idempotent_and_searchable(tmp_path):
    source = tmp_path / "source.db"
    index_path = tmp_path / "rag.db"
    _source_db(source)
    index = RagIndex(str(index_path), str(source), FakeEmbeddingClient())

    first = index.sync_rulings()
    second = index.sync_rulings()

    assert first["changed_rulings"] == 1
    assert first["written_chunks"] == 2
    assert second == {"changed_rulings": 0, "written_chunks": 0}
    query = FakeEmbeddingClient().embeddings(["battery cable"])[0]
    results = index.retrieve("battery cable", query)
    assert results[0]["ruling_no"] == "N10000"


def test_hts_import_and_exact_validation(tmp_path):
    source = tmp_path / "source.db"
    _source_db(source)
    index = RagIndex(str(tmp_path / "rag.db"), str(source), FakeEmbeddingClient())
    hts = tmp_path / "hts.json"
    hts.write_text(
        json.dumps(
            [
                {"htsno": "8544", "indent": "0", "description": "Insulated wire"},
                {
                    "htsno": "8544.42.90.00",
                    "indent": "1",
                    "description": "Other conductors",
                    "general": "2.6%",
                },
            ]
        ),
        encoding="utf-8",
    )
    result = index.sync_hts(str(hts))
    assert result["hts_entries"] == 2
    assert index.exact_hts("8544.42.9000")["description"] == "Other conductors"

def test_model_tax_code_must_be_in_backend_candidate_whitelist():
    class ExactIndex:
        calls = []

        def exact_hts(self, code):
            self.calls.append(code)
            return {
                "code": "9999.99.99.99",
                "description": "Unrelated but current entry",
                "parent_path": "",
            }

    index = ExactIndex()
    service = ClassificationService(index=index, client=FakeEmbeddingClient())
    result = service._validated_result(
        {
            "primary_hts_code": "9999.99.99.99",
            "confidence": "high",
            "used_ruling_numbers": ["N10000"],
        },
        {"english_query": "battery cable", "missing_information": []},
        [{
            "ruling_no": "N10000", "subject": "Battery cable", "ruling_date": "",
            "year": 2025, "hs_codes": ["8544.42.9000"], "status": "active",
            "detail_url": "https://rulings.cbp.gov/ruling/N10000", "section": "FACTS",
            "text": "A copper battery cable.",
        }],
        {"N10000": {
            "similarities": "产品名称和用途相同",
            "differences": "材料尚未说明",
        }},
        {"hts_version": "2026 Revision 11"},
        [{"code_digits": "8544429000"}],
    )
    assert result["primary"] is None
    assert index.calls == []

    assert result["references"][0]["similarities"] == ["产品名称和用途相同"]
    assert result["references"][0]["differences"] == ["材料尚未说明"]


def test_text_list_does_not_split_model_strings():
    assert _text_list("完整中文说明") == ["完整中文说明"]
    assert _text_list(["第一点", "", "第二点"]) == ["第一点", "第二点"]

def test_chat_embedding_and_reranker_use_independent_sources(monkeypatch):
    client = OpenAICompatibleClient(
        chat_base_url="https://chat.example/v1/chat/completions",
        chat_api_key="chat-key",
        chat_model="chat-model",
        chat_timeout=11,
        embedding_base_url="https://embed.example/v1/embeddings",
        embedding_api_key="embed-key",
        embedding_model="embed-model",
        embedding_timeout=22,
        reranker_base_url="https://rerank.example/v1/rerank",
        reranker_api_key="rerank-key",
        reranker_model="rerank-model",
        reranker_timeout=33,
    )
    assert client.configured()
    calls = []

    def fake_post(base_url, api_key, timeout, payload):
        calls.append((base_url, api_key, timeout, payload["model"]))
        if payload["model"] == "embed-model":
            return {"data": [{"index": 0, "embedding": [1.0, 0.0]}]}
        if payload["model"] == "rerank-model":
            return {"results": [{"index": 1, "relevance_score": 0.9}]}
        return {"choices": [{"message": {"content": '{"ok": true}'}}]}

    monkeypatch.setattr(client, "_post", fake_post)
    client.embeddings(["cable"])
    assert client.rerank("cable", ["first", "second"], 1) == [
        {"index": 1, "relevance_score": 0.9}
    ]
    assert client.chat_json("system", {"product": "cable"}) == {"ok": True}
    assert calls == [
        ("https://embed.example/v1/embeddings", "embed-key", 22, "embed-model"),
        ("https://rerank.example/v1/rerank", "rerank-key", 33, "rerank-model"),
        ("https://chat.example/v1/chat/completions", "chat-key", 11, "chat-model"),
    ]

def test_model_endpoint_is_used_verbatim(monkeypatch):
    urls = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"{}"

    def fake_urlopen(request, timeout):
        urls.append(request.full_url)
        return Response()

    monkeypatch.setattr("app.rag.urllib.request.urlopen", fake_urlopen)
    OpenAICompatibleClient._post(
        "https://api.example/v1/embeddings", "key", 10, {}
    )
    OpenAICompatibleClient._post(
        "https://api.example/v1", "key", 10, {}
    )
    assert urls == [
        "https://api.example/v1/embeddings",
        "https://api.example/v1",
    ]

def test_truncated_embedding_batch_is_split_and_retried(monkeypatch):
    client = OpenAICompatibleClient(
        embedding_base_url="https://embed.example/v1/embeddings",
        embedding_api_key="key",
        embedding_model="model",
    )
    batch_sizes = []

    def fake_post(base_url, api_key, timeout, payload):
        batch_sizes.append(len(payload["input"]))
        if len(payload["input"]) > 1:
            raise http.client.IncompleteRead(b"partial", 10)
        return {"data": [{"index": 0, "embedding": [1.0, 0.0]}]}

    monkeypatch.setattr(client, "_post", fake_post)
    vectors = client.embeddings(["one", "two"])
    assert len(vectors) == 2
    assert batch_sizes == [2, 1, 1]
