"""URL-001 URL 정규화."""

from dataclasses import dataclass
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from app.core.errors import AppError, ErrorCode

ALLOWED_SCHEMES = {"http", "https"}
DEFAULT_PORTS = {"http": 80, "https": 443}


@dataclass(frozen=True)
class NormalizedUrl:
    url: str
    scheme: str
    host: str
    port: int


def normalize_url(raw: str, max_length: int) -> NormalizedUrl:
    raw = raw.strip()
    if len(raw) > max_length:
        raise AppError(
            ErrorCode.URL_TOO_LONG, details=[{"field": "url", "reason": f"최대 {max_length}자"}]
        )

    try:
        parts = urlsplit(raw)
        port = parts.port
    except ValueError as e:
        raise AppError(ErrorCode.INVALID_URL, details=[{"field": "url", "reason": str(e)}]) from e

    scheme = parts.scheme.lower()
    if not scheme:
        raise AppError(
            ErrorCode.INVALID_URL, details=[{"field": "url", "reason": "스킴이 없습니다."}]
        )
    if scheme not in ALLOWED_SCHEMES:
        raise AppError(
            ErrorCode.UNSUPPORTED_SCHEME,
            details=[{"field": "url", "reason": f"{scheme} 스킴은 지원하지 않습니다."}],
        )
    # user:password@host 형식 거부 (API 명세 6.1)
    if parts.username is not None or parts.password is not None:
        raise AppError(
            ErrorCode.INVALID_URL,
            details=[{"field": "url", "reason": "사용자 정보가 포함된 URL은 지원하지 않습니다."}],
        )

    host = (parts.hostname or "").rstrip(".")
    if not host:
        raise AppError(
            ErrorCode.INVALID_URL, details=[{"field": "url", "reason": "호스트가 없습니다."}]
        )
    try:
        host = host.encode("idna").decode("ascii").lower()
    except UnicodeError as e:
        raise AppError(
            ErrorCode.INVALID_URL, details=[{"field": "url", "reason": "잘못된 도메인"}]
        ) from e

    port = port or DEFAULT_PORTS[scheme]
    netloc = f"[{host}]" if ":" in host else host
    if port != DEFAULT_PORTS[scheme]:
        netloc = f"{netloc}:{port}"

    path = quote(unquote(parts.path), safe="/%:@!$&'()*+,;=-._~") or "/"
    query = quote(unquote(parts.query), safe="=&%:@!$'()*+,;/?-._~")

    url = urlunsplit((scheme, netloc, path, query, ""))
    return NormalizedUrl(url=url, scheme=scheme, host=host, port=port)
