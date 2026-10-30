import asyncio
import ipaddress
import logging
import socket
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urljoin

import httpx

from app.core.errors import AppError, ErrorCode
from app.schemas.analysis import CheckResult
from app.services.analyses.parsing import ParsedUrl, normalize_url
from app.services.analyses.rules import UrlCatalog, evaluate, matches_domain, total_score

logger = logging.getLogger(__name__)

REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
USER_AGENT = "Mozilla/5.0 (compatible; QRSafeScan/1.0; +phishing-check)"


@dataclass(frozen=True)
class HopResponse:
    status_code: int
    location: str | None


class UrlProbe(Protocol):
    """DNS 조회와 단일 요청을 담당한다. 테스트에서는 네트워크 없는 가짜 구현으로 바꾼다."""

    async def resolve(self, host: str) -> list[str]: ...

    async def fetch(self, url: ParsedUrl, ip: str, timeout: float) -> HopResponse: ...


class HttpUrlProbe:
    async def resolve(self, host: str) -> list[str]:
        loop = asyncio.get_running_loop()
        try:
            infos = await loop.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        except (socket.gaierror, UnicodeError) as exc:
            raise AppError(ErrorCode.DNS_RESOLUTION_FAILED) from exc
        return list(dict.fromkeys(str(info[4][0]) for info in infos))

    async def fetch(self, url: ParsedUrl, ip: str, timeout: float) -> HopResponse:
        # 검증한 IP로 직접 접속해 DNS 재바인딩을 막고, Host 헤더와 SNI 는 원래 도메인을 쓴다
        extensions = {"sni_hostname": url.host} if url.scheme == "https" and not url.is_ip else {}
        headers = {"Host": url.host_header, "User-Agent": USER_AGENT, "Accept": "*/*"}
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False) as c:
            async with c.stream(
                "GET", url.url_for_ip(ip), headers=headers, extensions=extensions
            ) as response:
                # 본문은 읽지 않는다. 리디렉션 여부만 필요하다.
                return HopResponse(response.status_code, response.headers.get("location"))


@dataclass(frozen=True)
class AnalysisOutcome:
    hops: list[ParsedUrl]
    checks: list[CheckResult]
    score: int

    @property
    def original(self) -> ParsedUrl:
        return self.hops[0]

    @property
    def final(self) -> ParsedUrl:
        return self.hops[-1]


def _ensure_public(ips: list[str]) -> None:
    """루프백·사설·링크 로컬·메타데이터 등 공인 주소가 아닌 IP 가 하나라도 있으면 차단한다."""
    if not ips:
        raise AppError(ErrorCode.DNS_RESOLUTION_FAILED)
    for ip in ips:
        addr = ipaddress.ip_address(ip.split("%", 1)[0])
        if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
            addr = addr.ipv4_mapped
        if not addr.is_global or addr.is_multicast:
            raise AppError(ErrorCode.PRIVATE_NETWORK_TARGET)


async def _safe_ip(url: ParsedUrl, probe: UrlProbe) -> str:
    ips = [url.host] if url.is_ip else await probe.resolve(url.host)
    _ensure_public(ips)
    return ips[0]


async def trace_redirects(
    start: ParsedUrl, probe: UrlProbe, catalog: UrlCatalog, max_redirects: int, timeout: float
) -> tuple[list[ParsedUrl], bool]:
    """리디렉션을 한 단계씩 따라가며 매 단계 SSRF·차단 목록을 다시 검사한다 (URL-003, URL-009).

    반환값은 (방문한 URL 목록, 차단 목록 일치 여부). 차단 목록에 걸리면 그 주소에는 접속하지 않는다.
    """
    hops = [start]
    while True:
        current = hops[-1]
        if matches_domain(current.host, catalog.blocklist):
            return hops, True

        ip = await _safe_ip(current, probe)
        try:
            hop = await probe.fetch(current, ip, timeout)
        except httpx.TimeoutException as exc:
            raise AppError(ErrorCode.ANALYSIS_TIMEOUT) from exc
        except httpx.HTTPError as exc:
            raise AppError(ErrorCode.ANALYSIS_FAILED, "대상 사이트에 접속할 수 없습니다.") from exc

        if hop.status_code not in REDIRECT_STATUSES or not hop.location:
            return hops, False
        if len(hops) - 1 >= max_redirects:
            raise AppError(ErrorCode.REDIRECT_LIMIT_EXCEEDED)
        hops.append(normalize_url(urljoin(current.url, hop.location)))


async def analyze_url(
    raw_url: str, probe: UrlProbe, catalog: UrlCatalog, max_redirects: int, timeout: float
) -> AnalysisOutcome:
    start = normalize_url(raw_url)
    try:
        async with asyncio.timeout(timeout):
            hops, blocked = await trace_redirects(start, probe, catalog, max_redirects, timeout)
    except TimeoutError as exc:
        raise AppError(ErrorCode.ANALYSIS_TIMEOUT) from exc

    # URL-004: 단축 URL 은 최종 목적지로 판정한다. 목적지를 끝내 확인하지 못하면 판정하지 않는다.
    if not blocked and matches_domain(hops[-1].host, catalog.shorteners):
        raise AppError(ErrorCode.ANALYSIS_FAILED, "단축 URL의 최종 목적지를 확인하지 못했습니다.")

    checks = evaluate(hops, blocked, catalog)
    return AnalysisOutcome(hops=hops, checks=checks, score=total_score(checks))
