import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import ERROR_SPECS, AppError, ErrorCode

logger = logging.getLogger(__name__)


def _error_body(request: Request, code: str, message: str, details: list) -> dict:
    return {
        "success": False,
        "error": {"code": code, "message": message, "details": details},
        "requestId": getattr(request.state, "request_id", None),
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(request, exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"field": ".".join(str(p) for p in err["loc"] if p != "body"), "reason": err["msg"]}
            for err in exc.errors()
        ]
        code = ErrorCode.INVALID_REQUEST
        status, message = ERROR_SPECS[code]
        return JSONResponse(
            status_code=status, content=_error_body(request, code, message, details)
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND"}.get(
            exc.status_code, "HTTP_ERROR"
        )
        return JSONResponse(
            status_code=exc.status_code, content=_error_body(request, code, str(exc.detail), [])
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        # 스택 트레이스는 로그에만 남기고 응답에는 포함하지 않는다 (API 명세 6.2)
        logger.exception("Unhandled error on %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content=_error_body(request, "INTERNAL_SERVER_ERROR", "서버 내부 오류입니다.", []),
        )
