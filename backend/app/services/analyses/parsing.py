import ipaddress
import re
import socket
from dataclasses import dataclass
from urllib.parse import quote, urlsplit

import idna

from app.core.errors import AppError, ErrorCode

MAX_URL_LENGTH = 2048
DEFAULT_PORTS = {"http": 80, "https": 443}

_LABEL = re.compile(r"^[a-z0-9_](?:[a-z0-9_-]{0,61}[a-z0-9_])?$")
_NUMERIC_HOST = re.compile(r"^[0-9a-fx.]+$")
_CONTROL_CHARS = re.compile(r"[\x00-\x20\x7f]")


@dataclass(frozen=True)
class ParsedUrl:
    """정규화된 HTTP(S) URL (URL-001). host 는 소문자 ASCII(punycode) 또는 IP 주소."""

    scheme: str
    host: str
    port: int
    path_query: str
    has_userinfo: bool = False

    @property
    def is_ip(self) -> bool:
        return is_ip_address(self.host)

    @property
    def _netloc_host(self) -> str:
        return f"[{self.host}]" if ":" in self.host else self.host

    @property
    def host_header(self) -> str:
        if self.port == DEFAULT_PORTS[self.scheme]:
            return self._netloc_host
        return f"{self._netloc_host}:{self.port}"

    @property
    def url(self) -> str:
        return f"{self.scheme}://{self.host_header}{self.path_query}"

    def url_for_ip(self, ip: str) -> str:
        """검증한 IP로 직접 접속하기 위한 URL. Host 헤더·SNI 는 호출 측에서 원래 host 로 보낸다."""
        ip_host = f"[{ip}]" if ":" in ip else ip
        return f"{self.scheme}://{ip_host}:{self.port}{self.path_query}"


def is_ip_address(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def _normalize_host(hostname: str) -> str:
    host = hostname.rstrip(".").lower()
    if not host:
        raise AppError(ErrorCode.INVALID_URL)

    if ":" in host:
        try:
            return ipaddress.IPv6Address(host).compressed
        except ValueError as exc:
            raise AppError(ErrorCode.INVALID_URL) from exc

    # 2130706433, 0x7f.1 같은 축약·진법 표기도 IPv4 로 해석해 우회를 막는다
    if _NUMERIC_HOST.fullmatch(host) and not host.replace(".", "").isalpha():
        try:
            return socket.inet_ntoa(socket.inet_aton(host))
        except OSError:
            pass

    ascii_host = host
    if not host.isascii():
        # 국제화 도메인은 IDNA 2008(UTS #46)으로 Punycode 변환한다
        try:
            ascii_host = idna.encode(host, uts46=True).decode("ascii")
        except idna.IDNAError as exc:
            raise AppError(ErrorCode.INVALID_URL) from exc
    if len(ascii_host) > 253 or not all(_LABEL.fullmatch(p) for p in ascii_host.split(".")):
        raise AppError(ErrorCode.INVALID_URL)
    return ascii_host


def normalize_url(raw: str) -> ParsedUrl:
    text = raw.strip()
    if len(text) > MAX_URL_LENGTH:
        raise AppError(ErrorCode.URL_TOO_LONG)
    if not text or _CONTROL_CHARS.search(text):
        raise AppError(ErrorCode.INVALID_URL)

    parts = urlsplit(text)
    scheme = parts.scheme.lower()
    if not scheme:
        raise AppError(ErrorCode.INVALID_URL)
    if scheme not in DEFAULT_PORTS:
        raise AppError(ErrorCode.UNSUPPORTED_SCHEME)
    if not parts.netloc:
        raise AppError(ErrorCode.INVALID_URL)

    try:
        hostname = parts.hostname
        port = parts.port or DEFAULT_PORTS[scheme]
    except ValueError as exc:
        raise AppError(ErrorCode.INVALID_URL) from exc
    if not hostname:
        raise AppError(ErrorCode.INVALID_URL)

    path = quote(parts.path or "/", safe="/%:@!$&'()*+,;=-._~")
    query = quote(parts.query, safe="/?%:@!$&'()*+,;=-._~")
    return ParsedUrl(
        scheme=scheme,
        host=_normalize_host(hostname),
        port=port,
        path_query=f"{path}?{query}" if query else path,
        has_userinfo="@" in parts.netloc,
    )
