"""Official HTSUS/CBP legal document acquisition and page-preserving chunking."""
from __future__ import annotations

import hashlib
import io
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from app.errors import UpstreamError

USITC_GENERAL_RULES_URL = (
    "https://hts.usitc.gov/reststop/file"
    "?release=currentRelease&filename=finalCopy"
)
CBP_TARIFF_CLASSIFICATION_URL = "https://www.cbp.gov/sites/default/files/documents/icp017r2_3.pdf"


def default_legal_sources() -> list[dict[str, str]]:
    """Official public PDFs containing GRI, legal notes, and CBP guidance."""
    sources = [
        {"source_id": "usitc-current-hts", "source_type": "hts_legal",
         "title": "Current Harmonized Tariff Schedule of the United States",
         "scope": "auto", "url": USITC_GENERAL_RULES_URL},
        {"source_id": "cbp-tariff-classification", "source_type": "cbp_guide",
         "title": "CBP Tariff Classification", "scope": "general",
         "url": CBP_TARIFF_CLASSIFICATION_URL},
    ]
    return sources


def read_source_bytes(source: str, timeout: int = 120) -> bytes:
    if not re.match(r"^https?://", source):
        return Path(source).read_bytes()
    request = urllib.request.Request(
        source, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/pdf"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        result = subprocess.run(
            ["curl.exe", "-fsSL", source], capture_output=True, timeout=timeout
        )
        if result.returncode == 0:
            return result.stdout
        raise UpstreamError(f"官方法律 PDF 下载失败: {source}: {exc}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise UpstreamError(f"官方法律 PDF 下载失败: {source}: {exc}") from exc


def extract_pdf_pages(payload: bytes) -> list[str]:
    if not payload.startswith(b"%PDF-"):
        raise UpstreamError("官方法律资料响应不是 PDF")
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise UpstreamError("同步法律 PDF 前请安装 pypdf") from exc
    try:
        reader = PdfReader(io.BytesIO(payload))
        return [(page.extract_text() or "").strip() for page in reader.pages]
    except Exception as exc:
        raise UpstreamError(f"官方法律 PDF 解析失败: {exc}") from exc


def chunk_legal_pages(
    pages: list[str], source: dict[str, str], version: str, max_chars: int = 2400
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    current_scope = "general"
    current_title = source["title"]
    for page_number, page_text in enumerate(pages, 1):
        clean = re.sub(r"[ \t]+", " ", page_text.replace("\r", "")).strip()
        chapter_match = re.search(r"\bCHAPTER\s+(\d{1,2})\b", clean[:1200], re.I)
        if source["scope"] == "auto" and chapter_match:
            chapter = int(chapter_match.group(1))
            current_scope = f"chapter:{chapter:02d}"
            current_title = f"HTS Chapter {chapter}"
        scope = current_scope if source["scope"] == "auto" else source["scope"]
        title = current_title if source["scope"] == "auto" else source["title"]
        if not clean:
            continue
        paragraphs = [item.strip() for item in re.split(r"\n\s*\n", clean) if item.strip()]
        if not paragraphs:
            paragraphs = [clean]
        current = ""
        page_chunks: list[str] = []
        for paragraph in paragraphs:
            if current and len(current) + len(paragraph) + 2 > max_chars:
                page_chunks.append(current)
                current = ""
            while len(paragraph) > max_chars:
                if current:
                    page_chunks.append(current)
                    current = ""
                page_chunks.append(paragraph[:max_chars])
                paragraph = paragraph[max_chars:]
            current = f"{current}\n\n{paragraph}".strip()
        if current:
            page_chunks.append(current)
        for position, text in enumerate(page_chunks, 1):
            chunk_id = hashlib.sha256(
                f"{source['source_id']}\0{version}\0{page_number}\0{position}\0{text}".encode("utf-8")
            ).hexdigest()[:24]
            chunks.append({
                "chunk_id": chunk_id, "source_id": source["source_id"],
                "source_type": source["source_type"], "title": title,
                "scope": scope, "page": page_number, "text": text,
                "source_url": source["url"], "version": version,
                "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            })
    return chunks
