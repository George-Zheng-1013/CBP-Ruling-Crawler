"""裁定查询、详情、导出与原文 HTML 端点。

注意路由注册顺序：``/export`` 必须在 ``/{ruling_no}`` 之前定义，否则 "export"
会被 ``{ruling_no}`` 路径参数吞掉。
"""
import csv
import io
import json
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse

from app.db import DatabaseManager
from app.errors import NotFoundError, UpstreamError
from app.schemas import (
    Envelope,
    HtmlContent,
    PageResult,
    PdfBatchDownloadRequest,
    PdfBatchDownloadResult,
    PdfDownloadFailure,
    RulingDetail,
    RulingListItem,
    SearchParams,
)
from app.services.search_service import SearchService
from app.services.pdf_service import (
    REFERENCE_CASES_DIR,
    create_batch_directory,
    fetch_ruling_pdf,
)

router = APIRouter(prefix="/api/rulings", tags=["rulings"])

_db = DatabaseManager()
_service = SearchService(_db)

_EXPORT_FIELDS = [
    "ruling_no",
    "subject",
    "description",
    "hs_code",
    "hs_codes",
    "year",
    "detail_url",
    "ruling_date",
    "status",
    "parse_failed",
    "parse_error_msg",
]


@router.get("", summary="复合搜索裁定列表")
def list_rulings(params: SearchParams = Depends()) -> Envelope[PageResult[RulingListItem]]:
    """返回过滤 + 分页的裁定列表。"""
    page = _service.search(params)
    for row in page.items:
        if isinstance(row.get("hs_codes"), str):
            try:
                row["hs_codes"] = json.loads(row["hs_codes"])
            except (json.JSONDecodeError, TypeError):
                row["hs_codes"] = []
    items = [RulingListItem(**row) for row in page.items]
    result = PageResult[RulingListItem](
        items=items,
        total=page.total,
        page=page.page,
        page_size=page.page_size,
        total_pages=page.total_pages,
    )
    return Envelope(data=result)


@router.get("/export", summary="按当前筛选导出 CSV/JSON")
def export_rulings(
    format: str = Query("csv", pattern="^(csv|json)$"),
    params: SearchParams = Depends(),
) -> StreamingResponse:
    """导出当前筛选条件的 **全部** 结果（非当前页）。

    默认 CSV（UTF-8 with BOM 防 Excel 中文乱码），也可导出 JSON。
    """
    rows = _service.export_rows(params)

    if format == "json":
        payload = json.dumps(
            [{k: r.get(k, "") for k in _EXPORT_FIELDS} for r in rows],
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        return StreamingResponse(
            iter([payload]),
            media_type="application/json",
            headers={
                "Content-Disposition": 'attachment; filename="cbp_rulings.json"'
            },
        )

    # CSV：使用 utf-8-sig 编码（自动前置一个 BOM），保证 Excel 正确识别中文编码。
    # 注意：不要在此处再显式 write("\ufeff")，否则会产生双重 BOM 污染首列表头。
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=_EXPORT_FIELDS)
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k, "") for k in _EXPORT_FIELDS})
    data = output.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        iter([data]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="cbp_rulings.csv"'
        },
    )


@router.post("/download-pdfs", summary="保存多个案例 PDF 到本机")
def download_ruling_pdfs(
    body: PdfBatchDownloadRequest,
) -> Envelope[PdfBatchDownloadResult]:
    """逐份下载引用案例，并保存到产品名和时间组成的目录。"""
    ruling_numbers = list(
        dict.fromkeys(
            number.strip().upper()
            for number in body.ruling_numbers
            if number.strip()
        )
    )
    batch_dir = create_batch_directory(body.product_name, REFERENCE_CASES_DIR)
    downloaded: list[str] = []
    failed: list[PdfDownloadFailure] = []

    for ruling_no in ruling_numbers:
        row = _db.fetch_ruling_by_no(ruling_no)
        if row is None:
            failed.append(
                PdfDownloadFailure(ruling_no=ruling_no, reason="本地案例库中不存在")
            )
            continue
        try:
            content = fetch_ruling_pdf(row["ruling_no"])
            (batch_dir / f"{row['ruling_no']}.pdf").write_bytes(content)
            downloaded.append(row["ruling_no"])
        except (OSError, UpstreamError):
            failed.append(
                PdfDownloadFailure(ruling_no=ruling_no, reason="CBP 官方 PDF 获取失败")
            )

    if not downloaded:
        try:
            batch_dir.rmdir()
            Path(batch_dir.parent).rmdir()
        except OSError:
            pass
        raise UpstreamError("所有参考案例 PDF 均下载失败")

    return Envelope(
        data=PdfBatchDownloadResult(
            directory=str(batch_dir),
            downloaded=downloaded,
            failed=failed,
        )
    )


@router.get("/{ruling_no}/pdf", summary="下载单个案例 PDF")
def ruling_pdf(ruling_no: str) -> Response:
    """从 CBP 官方接口获取 PDF，并以附件形式返回。"""
    row = _db.fetch_ruling_by_no(ruling_no.strip().upper())
    if row is None:
        raise NotFoundError(f"ruling {ruling_no} not found")
    content = fetch_ruling_pdf(row["ruling_no"])
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{row["ruling_no"]}.pdf"'
            )
        },
    )


@router.get("/{ruling_no}", summary="裁定详情")
def ruling_detail(ruling_no: str) -> Envelope[RulingDetail]:
    """返回单条裁定的完整详情。"""
    row = _db.fetch_ruling_by_no(ruling_no)
    if row is None:
        raise NotFoundError(f"ruling {ruling_no} not found")
    detail = RulingDetail(
        ruling_no=row["ruling_no"],
        subject=row.get("subject", ""),
        description=row.get("description", ""),
        hs_code=row.get("hs_code", ""),
        hs_codes=row.get("hs_codes", []),
        year=row.get("year") or 0,
        ruling_date=row.get("ruling_date", ""),
        status=row.get("status", "active"),
        detail_url=row.get("detail_url", ""),
        parse_failed=row.get("parse_failed", False),
        parse_error_msg=row.get("parse_error_msg", ""),
    )
    return Envelope(data=detail)


@router.get("/{ruling_no}/html", summary="裁定原文 HTML（P2）")
def ruling_html(ruling_no: str) -> Envelope[HtmlContent]:
    """返回裁定原文 HTML / 纯文本（来自 html_store 表）。"""
    row = _db.fetch_html(ruling_no)
    if row is None:
        raise NotFoundError(f"html for ruling {ruling_no} not found")
    content = HtmlContent(
        html_content=row.get("html_content", ""),
        plain_text=row.get("plain_text", ""),
        fetch_status=row.get("fetch_status", 200),
    )
    return Envelope(data=content)
