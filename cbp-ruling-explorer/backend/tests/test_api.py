"""API 集成测试（TestClient）：envelope 结构、复合筛选、分页、详情、统计。"""
import sqlite3

TEST_DB = None  # 由 conftest 注入环境，这里用 client 直接验证


def test_health_envelope(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0 and body["message"] == "ok"
    assert body["data"]["service"] == "cbp-ruling-explorer"


def test_list_envelope_and_pagination(client):
    r = client.get("/api/rulings?page=1&page_size=5")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    d = body["data"]
    assert d["total"] == 17
    assert d["page"] == 1
    assert d["page_size"] == 5
    assert d["total_pages"] == 4
    assert len(d["items"]) == 5
    # 列表项字段精简
    assert set(d["items"][0].keys()) == {
        "ruling_no", "subject", "year", "hs_code", "status", "parse_failed"
    }


def test_list_compound_filter_and_logic(client):
    # year=2024 AND status=active
    r = client.get("/api/rulings?year=2024&status=active")
    d = r.json()["data"]
    assert all(i["year"] == 2024 and i["status"] == "active" for i in d["items"])
    assert d["total"] == 3
    # keyword OR 语义（subject/description）
    r2 = client.get("/api/rulings?keyword=toy")
    nos = [i["ruling_no"] for i in r2.json()["data"]["items"]]
    assert "N12345" in nos


def test_list_hs_code_cross_dot(client):
    # "8517" 应命中 "8517.62.0090"
    r = client.get("/api/rulings?hs_code=8517")
    d = r.json()["data"]
    assert d["total"] == 1
    assert d["items"][0]["hs_code"] == "8517.62.0090"


def test_detail_full_fields(client):
    r = client.get("/api/rulings/N12345")
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["ruling_no"] == "N12345"
    assert d["description"]
    assert d["detail_url"]
    assert d["hs_codes"] == ["9503.00.0000"]
    assert d["parse_failed"] is False


def test_detail_parse_failed(client):
    r = client.get("/api/rulings/N33333")
    d = r.json()["data"]
    assert d["parse_failed"] is True
    assert d["parse_error_msg"] == "HTML structure changed, description block not found"


def test_detail_404(client):
    r = client.get("/api/rulings/NOPE")
    assert r.status_code == 404
    assert r.json()["code"] == 404


def test_stats_overview_matches_db(client, test_db_path):
    r = client.get("/api/stats/overview")
    assert r.status_code == 200
    d = r.json()["data"]
    raw = sqlite3.connect(test_db_path)
    raw.row_factory = sqlite3.Row
    total = raw.execute("SELECT COUNT(*) c FROM rulings").fetchone()["c"]
    pf = raw.execute("SELECT COUNT(*) c FROM rulings WHERE parse_failed=1").fetchone()["c"]
    raw.close()
    assert d["total"] == total == 17
    assert d["parse_failed"] == pf == 2
    statuses = {s["status"]: s["count"] for s in d["by_status"]}
    assert statuses.get("active") == 13 and statuses.get("revoked") == 4


def test_html_endpoint_404_acceptable(client):
    # P2：测试库无 html_store 数据，返回 404 属可接受
    r = client.get("/api/rulings/N12345/html")
    assert r.status_code in (200, 404)


def test_validation_returns_4xx_not_5xx(client):
    """非法查询参数应返回 4xx（422/400），**不得**返回 500。

    ⚠️ 当前源码对 field_validator 失败（page=0/sort=bad/year=1800）返回 500，
    因为 errors.py 只捕获 RequestValidationError，未捕获依赖内抛出的
    pydantic.ValidationError。此测试断言正确行为，当前会失败 —— 见 Bug #2。
    """
    for q in ["page=0", "sort=bad", "year=1800"]:
        r = client.get(f"/api/rulings?{q}")
        assert r.status_code in (400, 422), f"{q} 期望 4xx，实际 {r.status_code}: {r.text}"
