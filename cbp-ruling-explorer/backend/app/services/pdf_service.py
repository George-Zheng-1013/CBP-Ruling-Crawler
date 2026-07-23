"""Fetch CBP ruling PDFs and create safe local batch directories."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from app.config import BACKEND_DIR
from app.errors import UpstreamError

CBP_BASE_URL = "https://rulings.cbp.gov"
REFERENCE_CASES_DIR = BACKEND_DIR.parent.parent / "参考案例"
_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def sanitize_product_name(product_name: str) -> str:
    """Return a Windows-safe folder name without accepting path components."""
    cleaned = _INVALID_FILENAME_CHARS.sub("_", product_name.strip())
    cleaned = cleaned.rstrip(" .")[:120]
    if not cleaned:
        cleaned = "未命名产品"
    if cleaned.split(".", 1)[0].upper() in _WINDOWS_RESERVED_NAMES:
        cleaned = f"_{cleaned}"
    return cleaned


def create_batch_directory(
    product_name: str,
    root: Path = REFERENCE_CASES_DIR,
    now: datetime | None = None,
) -> Path:
    """Create ``root/product/timestamp`` without overwriting an earlier batch."""
    root = root.resolve()
    product_dir = (root / sanitize_product_name(product_name)).resolve()
    if root != product_dir and root not in product_dir.parents:
        raise ValueError("invalid product directory")

    product_dir.mkdir(parents=True, exist_ok=True)
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    batch_dir = product_dir / timestamp
    suffix = 2
    while batch_dir.exists():
        batch_dir = product_dir / f"{timestamp}_{suffix}"
        suffix += 1
    batch_dir.mkdir()
    return batch_dir


def fetch_ruling_pdf(ruling_no: str, timeout: int = 60) -> bytes:
    """Fetch and validate one PDF from the official CROSS endpoints."""
    number = ruling_no.strip().upper()
    metadata_url = f"{CBP_BASE_URL}/api/ruling/{quote(number)}"
    try:
        metadata_request = urllib.request.Request(
            metadata_url,
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        )
        with urllib.request.urlopen(metadata_request, timeout=timeout) as response:
            metadata = json.loads(response.read().decode("utf-8"))

        collection = str(metadata.get("collection") or "").lower()
        ruling_date = str(metadata.get("rulingDate") or "")
        official_number = str(metadata.get("rulingNumber") or number).upper()
        if collection not in {"ny", "hq"} or len(ruling_date) < 4:
            raise ValueError("invalid ruling metadata")

        pdf_url = (
            f"{CBP_BASE_URL}/api/getdoc/{quote(collection)}/"
            f"{quote(ruling_date[:4])}/{quote(official_number)}.pdf"
        )
        pdf_request = urllib.request.Request(
            pdf_url,
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/pdf"},
        )
        with urllib.request.urlopen(pdf_request, timeout=timeout) as response:
            content = response.read()
    except (OSError, ValueError, json.JSONDecodeError,
            urllib.error.HTTPError, urllib.error.URLError) as exc:
        raise UpstreamError(f"无法从 CBP 获取案例 {number} 的 PDF") from exc


    if not content.startswith(b"%PDF-"):
        raise UpstreamError(f"CBP 返回的案例 {number} 文件不是有效 PDF")
    return content
