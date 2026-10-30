import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.ids import new_id

logger = logging.getLogger("app.access")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """X-Request-ID 를 받아 쓰거나 새로 발급하고, 처리 시간을 기록한다 (NFR-008)."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get("X-Request-ID")
        request_id = incoming[:100] if incoming else new_id("req")
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Request-ID"] = request_id
        # 쿼리 문자열은 기록하지 않는다 (API 명세 6.2)
        logger.info(
            "%s %s %s %.1fms rid=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request_id,
        )
        return response
