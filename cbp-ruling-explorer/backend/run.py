"""Uvicorn 启动入口。

启动 CBP Ruling Explorer 只读查询后端服务。
"""
import uvicorn

from app.config import HOST, PORT


def main() -> None:
    """启动 ASGI 服务器。"""
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)


if __name__ == "__main__":
    main()
