"""URL-003 리디렉션 추적."""

from dataclasses import dataclass, field
from urllib.parse import urljoin

import httpx

from app.analyzer.normalizer import NormalizedUrl, normalize_url
from app.analyzer.ssrf import resolve_public_ips
from app.core.errors import AppError, ErrorCode

REDIRECT_STATUSES = {301, 302, 303, 307, 308}
USER_AGENT = "QRPhishingDetector/1.0 (+url-safety-check)"


@dataclass
class RedirectTrace:
    final: NormalizedUrl
    chain: list[str] = field(default_factory=list)

    @property
    def redirect_count(self) -> int:
        return len(self.chain) - 1


async def trace_redirects(
    start: NormalizedUrl, *, max_redirects: int, max_url_length: int, timeout: float
) -> RedirectTrace:
    """모든 홉에서 DNS 를 다시 확인하며 리디렉션을 수동으로 따라간다.

    응답 본문은 읽지 않는다 (API 명세 6.1).
    TODO: DNS 리바인딩 완전 방지를 위해 검증한 IP 로 연결을 고정(pinning)하는 transport 적용
    """
    current = start
    chain = [current.url]

    async with httpx.AsyncClient(
        follow_redirects=False,
        timeout=timeout,
        headers={"User-Agent": USER_AGENT},
        trust_env=False,
    ) as client:
        while True:
            await resolve_public_ips(current.host)
            try:
                async with client.stream("GET", current.url) as resp:
                    status = resp.status_code
                    location = resp.headers.get("location")
            except httpx.TimeoutException as e:
                raise AppError(ErrorCode.ANALYSIS_TIMEOUT) from e
            except httpx.HTTPError as e:
                raise AppError(
                    ErrorCode.ANALYSIS_FAILED, "대상 사이트에 연결할 수 없습니다."
                ) from e

            if status not in REDIRECT_STATUSES or not location:
                return RedirectTrace(final=current, chain=chain)

            if len(chain) > max_redirects:
                raise AppError(ErrorCode.REDIRECT_LIMIT_EXCEEDED)

            current = normalize_url(urljoin(current.url, location), max_url_length)
            chain.append(current.url)
