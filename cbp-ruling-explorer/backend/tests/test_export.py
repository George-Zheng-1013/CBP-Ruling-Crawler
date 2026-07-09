"""导出端点（CSV/JSON）单测 + 只读一致性。"""
import csv
import io
import json

EXPORT_FIELDS = [
    "ruling_no", "subject", "description", "hs_code", "hs_codes", "year",
    "detail_url", "ruling_date", "status", "parse_failed", "parse_error_msg",
]


def test_export_csv_single_bom(client):
    """CSV 应为 UTF-8 BOM（且**仅一个** BOM），首列表头不得被 BOM 字符污染。

    ⚠️ 当前源码在 routers/rulings.py 中先 write('\\ufeff') 又用 utf-8-sig 编码，
    产生双重 BOM，导致首列名变为 '\\ufeffruling_no'。此测试断言正确行为，
    当前会失败 —— 见反馈工程师的 Bug #1。
    """
    r = client.get("/api/rulings/export?format=csv")
    assert r.status_code == 200
    raw = r.content
    # 仅一个 BOM
    assert raw[:3] == b"\xef\xbb\xbf", "缺少 UTF-8 BOM"
    assert raw[3:6] != b"\xef\xbb\xbf", "出现双重 BOM（源码 Bug）"
    # 用 utf-8-sig 解码后首列名必须干净
    text = raw.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    header = next(reader)
    assert header[0] == "ruling_no", f"首列表头被 BOM 污染: {header[0]!r}"


def test_export_csv_full_set_not_just_page(client):
    r = client.get("/api/rulings/export?format=csv")
    text = r.content.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    # 1 header + 17 data
    assert len(rows) == 18
    # 筛选后导出应为筛选全集
    r2 = client.get("/api/rulings/export?format=csv&year=2019")
    rows2 = list(csv.reader(io.StringIO(r2.content.decode("utf-8-sig"))))
    assert len(rows2) == 3  # 2019 年 2 条 + header


def test_export_json_full_set(client):
    r = client.get("/api/rulings/export?format=json")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 17
    assert set(EXPORT_FIELDS).issubset(set(data[0].keys()))


def test_export_json_filtered_matches_db(client):
    # 通过端点验证筛选导出与 DB 聚合一致
    r = client.get("/api/rulings/export?format=json&status=revoked")
    data = r.json()
    assert len(data) == 4  # seed 中 4 条 revoked
    assert all(d["status"] == "revoked" for d in data)


def test_export_invalid_format_rejected(client):
    r = client.get("/api/rulings/export?format=xml")
    # 应为 4xx（400 或 422）
    assert r.status_code in (400, 422)
