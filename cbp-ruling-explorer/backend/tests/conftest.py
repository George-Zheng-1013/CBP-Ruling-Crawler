"""pytest 共享 fixture。

在导入任何 app 模块之前，将 CBP_DB_PATH 指向联调测试库（只读消费者本就只读，
这里只是保证单测不触碰爬虫源库）。测试库由 data/test/setup_test_db.py 生成。
"""
import os
import sys
import sqlite3

# backend/ 目录
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# cbp-ruling-explorer/ 根目录
ROOT_DIR = os.path.dirname(BACKEND_DIR)
TEST_DB = os.path.join(ROOT_DIR, "data", "test", "cbp_rulings_test.db")

# 必须在 import app 之前设置，使 config 读取到测试库
os.environ["CBP_DB_PATH"] = TEST_DB
# 让 backend/ 可被 import
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def test_db_path() -> str:
    """联调测试库绝对路径（必须已存在且 rulings>0）。"""
    assert os.path.isfile(TEST_DB), f"测试库不存在: {TEST_DB}，请先运行 data/test/setup_test_db.py"
    conn = sqlite3.connect(TEST_DB)
    n = conn.execute("SELECT COUNT(*) FROM rulings").fetchone()[0]
    conn.close()
    assert n > 0, "测试库 rulings 表为空"
    return TEST_DB


@pytest.fixture()
def client():
    """FastAPI TestClient（基于测试库）。"""
    from fastapi.testclient import TestClient
    import app.main as m

    with TestClient(m.app) as c:
        yield c
