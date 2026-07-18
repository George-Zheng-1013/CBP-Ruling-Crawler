"""FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.errors import register_exception_handlers
from app.routers import classify, crawl, rulings, stats


def create_app() -> FastAPI:
    app = FastAPI(
        title="CBP Ruling Explorer",
        description="CBP 裁定查询与案例驱动的 HTSUS 智能归类 API。",
        version="1.1.0",
    )
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
    app.include_router(classify.router)
    register_exception_handlers(app)

    @app.get("/", tags=["health"])
    def health() -> dict:
        return {
            "code": 0,
            "message": "ok",
            "data": {"service": "cbp-ruling-explorer"},
        }

    return app


app = create_app()
