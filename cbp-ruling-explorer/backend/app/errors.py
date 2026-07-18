"""Application error types and uniform envelope handlers."""
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError


class AppError(Exception):
    code: int = 1
    message: str = "error"
    http_status: int = 400

    def __init__(
        self,
        message: str | None = None,
        code: int | None = None,
        http_status: int | None = None,
    ) -> None:
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code
        if http_status is not None:
            self.http_status = http_status
        super().__init__(self.message)


class BadRequestError(AppError):
    code = 400
    message = "bad request"
    http_status = 400


class NotFoundError(AppError):
    code = 404
    message = "not found"
    http_status = 404


class UpstreamError(AppError):
    code = 502
    message = "upstream service error"
    http_status = 502


class ServiceUnavailableError(AppError):
    code = 503
    message = "service unavailable"
    http_status = 503


class InternalError(AppError):
    code = 500
    message = "internal error"
    http_status = 500


def _envelope(code: int, message: str, data: Any = None) -> Dict[str, Any]:
    return {"code": code, "message": message, "data": data}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content=_envelope(exc.code, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=_envelope(400, "invalid request parameters"),
        )

    @app.exception_handler(ValidationError)
    async def _handle_pydantic_validation(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_envelope(422, "invalid request parameters"),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=_envelope(500, "internal server error"),
        )
