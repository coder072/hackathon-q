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
from app.services.analyses.rules import (
    SUSPICIOUS_MIN_SCORE,
    UrlCatalog,
    evaluate,
    matches_domain,
    total_score,
)

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


async def _fetch(
    client: httpx.AsyncClient, url: ParsedUrl, ip: str, timeout: float
) -> httpx.Response:
    # 검증한 IP로 직접 접속해 DNS 재바인딩을 막고, Host 헤더와 TLS SNI 는 원래 도메인을 쓴다
    extensions = {"sni_hostname": url.host} if url.scheme == "https" and not url.is_ip else {}
    headers = {"Host": url.host_header, "User-Agent": USER_AGENT, "Accept": "*/*"}
    request = client.build_request(
        "GET", url.url_for_ip(ip), headers=headers, extensions=extensions, timeout=timeout
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


@dataclass(frozen=True)
class Trace:
    hops: list[ParsedUrl]
    blocked: bool
    # 접속 실패·시간 초과로 추적을 멈췄으면 그 오류. hops 는 그때까지 확인한 주소다
    unreachable: AppError | None = None


async def trace_redirects(
    start: ParsedUrl,
    client: httpx.AsyncClient,
    resolve: Resolver,
    catalog: UrlCatalog,
    max_redirects: int,
    deadline: float,
) -> Trace:
    """리디렉션을 한 단계씩 따라가며 매 단계 SSRF·차단 목록을 다시 검사한다 (URL-003, URL-009).

    차단 목록에 걸리면 그 주소에는 접속하지 않는다. 대상 서버에 접속하지 못하면 오류로 끝내지 않고
    그때까지 확인한 주소를 돌려준다 (판정 여부는 analyze_url 이 점수로 정한다, #26).
    """
    loop = asyncio.get_running_loop()
    hops = [start]
    while True:
        current = hops[-1]
        if matches_domain(current.host, catalog.blocklist):
            return Trace(hops, blocked=True)

        ip = await _safe_ip(current, resolve)
        # 전체 제한 시간 안에서 판정할 수 있도록 남은 시간만 기다린다
        remaining = deadline - loop.time()
        if remaining <= 0:
            return Trace(hops, blocked=False, unreachable=AppError(ErrorCode.ANALYSIS_TIMEOUT))
        try:
            response = await _fetch(client, current, ip, remaining)
        except httpx.TimeoutException:
            return Trace(hops, blocked=False, unreachable=AppError(ErrorCode.ANALYSIS_TIMEOUT))
        except httpx.HTTPError:
            error = AppError(ErrorCode.ANALYSIS_FAILED, "대상 사이트에 접속할 수 없습니다.")
            return Trace(hops, blocked=False, unreachable=error)

        location = response.headers.get("location")
        if response.status_code not in REDIRECT_STATUSES or not location:
            return Trace(hops, blocked=False)
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
    loop = asyncio.get_running_loop()
    # 접속 단계는 전체 제한 시간보다 조금 일찍 끊어, 남은 시간에 확인한 주소로 판정한다
    deadline = loop.time() + timeout * 0.9
    try:
        async with (
            asyncio.timeout(timeout),
            httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False) as client,
        ):
            trace = await trace_redirects(start, client, resolve, catalog, max_redirects, deadline)
    except TimeoutError as exc:
        raise AppError(ErrorCode.ANALYSIS_TIMEOUT) from exc
    hops, blocked = trace.hops, trace.blocked

    # URL-004: 단축 URL 은 최종 목적지로 판정한다. 목적지를 끝내 확인하지 못하면 판정하지 않는다.
    if not blocked and matches_domain(hops[-1].host, catalog.shorteners):
        raise AppError(ErrorCode.ANALYSIS_FAILED, "단축 URL의 최종 목적지를 확인하지 못했습니다.")

    checks = evaluate(hops, blocked, catalog, unreachable=trace.unreachable is not None)
    score = total_score(checks)
    # 접속하지 못했어도 URL 신호만으로 피싱 의심(4점 이상)이면 판정한다. 그보다 낮으면 리디렉션 끝에
    # 위험한 목적지가 있을 수 있어 안전으로 판정하지 않고 오류로 응답한다 (API-AC-03, #26)
    if trace.unreachable is not None and score < SUSPICIOUS_MIN_SCORE:
        raise trace.unreachable
    return AnalysisOutcome(hops=hops, checks=checks, score=score)
