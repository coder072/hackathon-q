"""URL-002, 005~008 검사 항목과 점수 (기능명세 5. 위험 점수 기준)."""

from enum import StrEnum
from urllib.parse import urlsplit

from app.analyzer.lookalike import find_impersonated_brand, registrable_domain
from app.analyzer.normalizer import NormalizedUrl
from app.analyzer.ssrf import parse_ip_host
from app.schemas.analysis import CheckResult


class CheckCode(StrEnum):
    HTTPS_NOT_USED = "HTTPS_NOT_USED"
    LOOKALIKE_DOMAIN = "LOOKALIKE_DOMAIN"
    SUSPICIOUS_URL_STRUCTURE = "SUSPICIOUS_URL_STRUCTURE"
    DIRECT_IP_ACCESS = "DIRECT_IP_ACCESS"
    BLOCKLIST_MATCH = "BLOCKLIST_MATCH"
    EXCESSIVE_REDIRECTS = "EXCESSIVE_REDIRECTS"
    ALLOWLIST_MATCH = "ALLOWLIST_MATCH"


SCORES: dict[CheckCode, int] = {
    CheckCode.HTTPS_NOT_USED: 1,
    CheckCode.LOOKALIKE_DOMAIN: 4,
    CheckCode.SUSPICIOUS_URL_STRUCTURE: 1,
    CheckCode.DIRECT_IP_ACCESS: 3,
    CheckCode.BLOCKLIST_MATCH: 10,
    CheckCode.EXCESSIVE_REDIRECTS: 1,
    CheckCode.ALLOWLIST_MATCH: 0,
}

# URL-006 구조 검사 기준값
LONG_URL_THRESHOLD = 100
MAX_SUBDOMAIN_DEPTH = 3
SUSPICIOUS_KEYWORDS = ("login", "verify", "account", "secure", "update", "signin", "wallet", "bank")


def _result(code: CheckCode, detected: bool, message: str) -> CheckResult:
    return CheckResult(
        code=code, detected=detected, score=SCORES[code] if detected else 0, message=message
    )


def check_https(final: NormalizedUrl) -> CheckResult:
    detected = final.scheme != "https"
    return _result(
        CheckCode.HTTPS_NOT_USED,
        detected,
        "HTTPS를 사용하지 않습니다." if detected else "HTTPS로 암호화된 연결을 사용합니다.",
    )


def check_lookalike(final: NormalizedUrl) -> CheckResult:
    brand = None if parse_ip_host(final.host) else find_impersonated_brand(final.host)
    return _result(
        CheckCode.LOOKALIKE_DOMAIN,
        brand is not None,
        f"유명 서비스({brand})와 유사한 도메인입니다." if brand else "유사 도메인 패턴이 없습니다.",
    )


def check_structure(final: NormalizedUrl) -> CheckResult:
    reasons: list[str] = []
    if len(final.url) > LONG_URL_THRESHOLD:
        reasons.append("URL이 지나치게 깁니다")
    if not parse_ip_host(final.host):
        sub = final.host.removesuffix(registrable_domain(final.host)).strip(".")
        if sub and sub.count(".") + 1 >= MAX_SUBDOMAIN_DEPTH:
            reasons.append("하위 도메인이 많습니다")
    path = urlsplit(final.url).path.lower()
    if "@" in final.url or "//" in path:
        reasons.append("URL에 의심스러운 특수문자가 포함되어 있습니다")
    if any(k in final.host or k in path for k in SUSPICIOUS_KEYWORDS) and reasons:
        reasons.append("로그인·인증 유도 키워드가 포함되어 있습니다")

    return _result(
        CheckCode.SUSPICIOUS_URL_STRUCTURE,
        bool(reasons),
        ", ".join(reasons) + "." if reasons else "URL 구조에 이상이 없습니다.",
    )


def check_direct_ip(final: NormalizedUrl) -> CheckResult:
    detected = parse_ip_host(final.host) is not None
    return _result(
        CheckCode.DIRECT_IP_ACCESS,
        detected,
        "도메인 대신 IP 주소를 사용합니다." if detected else "도메인 주소를 사용합니다.",
    )


def check_redirects(redirect_count: int, threshold: int) -> CheckResult:
    detected = redirect_count > threshold
    return _result(
        CheckCode.EXCESSIVE_REDIRECTS,
        detected,
        f"리디렉션이 {redirect_count}회 발생했습니다."
        if detected
        else "리디렉션 횟수가 정상입니다.",
    )


def check_blocklist(final: NormalizedUrl, domains: set[str], urls: set[str]) -> CheckResult:
    reg = registrable_domain(final.host)
    detected = final.url in urls or final.host in domains or reg in domains
    return _result(
        CheckCode.BLOCKLIST_MATCH,
        detected,
        "피싱·악성 URL 차단 목록과 일치합니다." if detected else "차단 목록에 없습니다.",
    )


def check_allowlist(final: NormalizedUrl, domains: set[str]) -> CheckResult:
    detected = final.host in domains or registrable_domain(final.host) in domains
    return _result(
        CheckCode.ALLOWLIST_MATCH,
        detected,
        "검증된 공식 도메인입니다." if detected else "허용 목록에 없는 도메인입니다.",
    )
