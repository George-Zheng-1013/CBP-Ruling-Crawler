"""FastAPI 应用入口：应用实例、CORS、路由注册与全局异常处理。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.errors import register_exception_handlers
from app.routers import rulings, stats, crawl


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用。"""
    app = FastAPI(
        title="CBP Ruling Explorer",
        description="对 CBP 裁定数据库的只读查询 API。",
        version="1.0.0",
    )

    # CORS：仅放行配置中的前端源。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(rulings.router)
    app.include_router(stats.router)
    app.include_router(crawl.router)

    register_exception_handlers(app)

    # TODO(P2): 如需上公网，可在此启用 X-API-Key 中间件钩子。
    @app.get("/", tags=["health"])
    def health() -> dict:
        return {"code": 0, "message": "ok",
                "data": {"service": "cbp-ruling-explorer"}}

    return app


app = create_app()
