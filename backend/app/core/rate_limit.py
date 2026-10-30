from slowapi import Limiter
from starlette.requests import Request


def client_ip(request: Request) -> str:
    """요청 제한 기준 IP. Vercel 프록시를 거치므로 X-Forwarded-For 의 첫 번째 값을 쓴다."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    first = forwarded.split(",", 1)[0].strip()
    if first:
        return first
    return request.client.host if request.client else "unknown"


# 엔드포인트에서 @limiter.limit(lambda: get_settings().analysis_rate_limit) 처럼 사용한다.
# 단일 컨테이너 기준 인메모리 저장소. 인스턴스를 늘리면 storage_uri 로 Redis 를 지정한다.
limiter = Limiter(key_func=client_ip)
