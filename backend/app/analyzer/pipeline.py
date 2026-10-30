import asyncio
from dataclasses import dataclass

from app.analyzer import checks as c
from app.analyzer.normalizer import NormalizedUrl, normalize_url
from app.analyzer.redirects import trace_redirects
from app.analyzer.scoring import decide
from app.analyzer.ssrf import parse_ip_host
from app.core.config import Settings
from app.core.errors import AppError, ErrorCode
from app.schemas.analysis import CheckResult, Verdict


@dataclass
class ListSnapshot:
    blocked_domains: set[str]
    blocked_urls: set[str]
    allowed_domains: set[str]


@dataclass
class PipelineResult:
    original: NormalizedUrl
    final: NormalizedUrl
    redirect_count: int
    checks: list[CheckResult]
    score: int
    verdict: Verdict


async def run_analysis(raw_url: str, lists: ListSnapshot, settings: Settings) -> PipelineResult:
    original = normalize_url(raw_url, settings.max_url_length)

    # IP 리터럴은 DNS 조회 없이 바로 SSRF 검사 대상
    if (ip := parse_ip_host(original.host)) is not None and (not ip.is_global or ip.is_multicast):
        raise AppError(ErrorCode.PRIVATE_NETWORK_TARGET)

    try:
        async with asyncio.timeout(settings.analysis_timeout_seconds):
            trace = await trace_redirects(
                original,
                max_redirects=settings.max_redirects,
                max_url_length=settings.max_url_length,
                timeout=settings.analysis_timeout_seconds,
            )
    except TimeoutError as e:
        raise AppError(ErrorCode.ANALYSIS_TIMEOUT) from e

    final = trace.final
    results = [
        c.check_blocklist(final, lists.blocked_domains, lists.blocked_urls),
        c.check_https(final),
        c.check_lookalike(final),
        c.check_structure(final),
        c.check_direct_ip(final),
        c.check_redirects(trace.redirect_count, settings.excessive_redirect_threshold),
        c.check_allowlist(final, lists.allowed_domains),
    ]
    score, verdict = decide(results)
    return PipelineResult(
        original=original,
        final=final,
        redirect_count=trace.redirect_count,
        checks=results,
        score=score,
        verdict=verdict,
    )
