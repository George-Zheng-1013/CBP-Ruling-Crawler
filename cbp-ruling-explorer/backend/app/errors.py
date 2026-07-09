"""应用错误类型与统一 envelope 异常处理器。

所有响应都遵循 ``{code, message, data}`` 结构。业务错误通过抛出的 ``AppError``
子类被全局异常处理器转换为 envelope 返回，避免散落的 JSONResponse。
"""
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError


class AppError(Exception):
    """预期内应用错误的基类。

    Attributes:
        code: 响应 envelope 中的业务错误码。
        message: 人类可读的错误信息。
        http_status: 对应的 HTTP 状态码。
    """

    code: int = 1
    message: str = "error"
    http_status: int = 400

    def __init__(
        self,
        message: str | None = None,
        code: int | None = None,
        http_status: int | None = None,
    ) -> None:
        """构造应用错误。

        Args:
            message: 可选的覆盖错误信息。
            code: 可选的覆盖业务码。
            http_status: 可选的覆盖 HTTP 状态码。
        """
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code
        if http_status is not None:
            self.http_status = http_status
        super().__init__(self.message)


class BadRequestError(AppError):
    """参数非法（400）。"""

    code = 400
    message = "bad request"
    http_status = 400


class NotFoundError(AppError):
    """资源未找到（404）。"""

    code = 404
    message = "not found"
    http_status = 404


class InternalError(AppError):
    """服务内部错误（500）。"""

    code = 500
    message = "internal error"
    http_status = 500


def _envelope(code: int, message: str, data: Any = None) -> Dict[str, Any]:
    """构造统一的响应 envelope。"""
    return {"code": code, "message": message, "data": data}


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器，保证所有异常都以 envelope 形式返回。"""

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
        # ``SearchParams`` 作为 Depends() 依赖实例化时，field_validator 抛出的
        # ``ValueError`` 会表现为普通的 pydantic.ValidationError（非请求层），
        # 必须单独捕获，否则会落到通用 Exception 处理器返回 500。
        # RequestValidationError 是其子类，FastAPI 会优先匹配更具体的处理器。
        return JSONResponse(
            status_code=422,
            content=_envelope(422, "invalid request parameters"),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # 生产环境应记录日志；此处仅返回通用错误，避免泄露内部细节。
        return JSONResponse(
            status_code=500,
            content=_envelope(500, "internal server error"),
        )
