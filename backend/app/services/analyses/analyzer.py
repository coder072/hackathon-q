import asyncio
import ipaddress
import logging
import socket
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx

from app.core.errors import AppError, ErrorCode
from app.schemas.analysis import CheckResult
from app.services.analyses.parsing import ParsedUrl, normalize_url
from app.services.analyses.rules import UrlCatalog, evaluate, matches_domain, total_score

logger = logging.getLogger(__name__)

REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
USER_AGENT = "Mozilla/5.0 (compatible; QRSafeScan/1.0; +phishing-check)"


Resolver = Callable[[str], Awaitable[list[str]]]


async def resolve_host(host: str) -> list[str]:
    """시스템 DNS 로 host 의 IP 목록을 조회한다. 테스트에서는 가짜 Resolver 로 바꾼다."""
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError) as exc:
        raise AppError(ErrorCode.DNS_RESOLUTION_FAILED) from exc
    return list(dict.fromkeys(str(info[4][0]) for info in infos))


async def _fetch(client: httpx.AsyncClient, url: ParsedUrl, ip: str) -> httpx.Response:
    # 검증한 IP로 직접 접속해 DNS 재바인딩을 막고, Host 헤더와 TLS SNI 는 원래 도메인을 쓴다
    extensions = {"sni_hostname": url.host} if url.scheme == "https" and not url.is_ip else {}
    headers = {"Host": url.host_header, "User-Agent": USER_AGENT, "Accept": "*/*"}
    request = client.build_request(
        "GET", url.url_for_ip(ip), headers=headers, extensions=extensions
    )
    # 본문은 읽지 않는다. 상태 코드와 Location 헤더만 필요하다.
    response = await client.send(request, stream=True)
    await response.aclose()
    return response


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


async def _safe_ip(url: ParsedUrl, resolve: Resolver) -> str:
    ips = [url.host] if url.is_ip else await resolve(url.host)
    _ensure_public(ips)
    return ips[0]


async def trace_redirects(
    start: ParsedUrl,
    client: httpx.AsyncClient,
    resolve: Resolver,
    catalog: UrlCatalog,
    max_redirects: int,
) -> tuple[list[ParsedUrl], bool]:
    """리디렉션을 한 단계씩 따라가며 매 단계 SSRF·차단 목록을 다시 검사한다 (URL-003, URL-009).

    반환값은 (방문한 URL 목록, 차단 목록 일치 여부). 차단 목록에 걸리면 그 주소에는 접속하지 않는다.
    """
    hops = [start]
    while True:
        current = hops[-1]
        if matches_domain(current.host, catalog.blocklist):
            return hops, True

        ip = await _safe_ip(current, resolve)
        try:
            response = await _fetch(client, current, ip)
        except httpx.TimeoutException as exc:
            raise AppError(ErrorCode.ANALYSIS_TIMEOUT) from exc
        except httpx.HTTPError as exc:
            raise AppError(ErrorCode.ANALYSIS_FAILED, "대상 사이트에 접속할 수 없습니다.") from exc

        location = response.headers.get("location")
        if response.status_code not in REDIRECT_STATUSES or not location:
            return hops, False
        if len(hops) - 1 >= max_redirects:
            raise AppError(ErrorCode.REDIRECT_LIMIT_EXCEEDED)
        hops.append(normalize_url(urljoin(current.url, location)))


async def analyze_url(
    raw_url: str,
    resolve: Resolver,
    catalog: UrlCatalog,
    max_redirects: int,
    timeout: float,
) -> AnalysisOutcome:
    start = normalize_url(raw_url)
    try:
        async with (
            asyncio.timeout(timeout),
            httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False) as client,
        ):
            hops, blocked = await trace_redirects(start, client, resolve, catalog, max_redirects)
    except TimeoutError as exc:
        raise AppError(ErrorCode.ANALYSIS_TIMEOUT) from exc

    # URL-004: 단축 URL 은 최종 목적지로 판정한다. 목적지를 끝내 확인하지 못하면 판정하지 않는다.
    if not blocked and matches_domain(hops[-1].host, catalog.shorteners):
        raise AppError(ErrorCode.ANALYSIS_FAILED, "단축 URL의 최종 목적지를 확인하지 못했습니다.")

    checks = evaluate(hops, blocked, catalog)
    return AnalysisOutcome(hops=hops, checks=checks, score=total_score(checks))
