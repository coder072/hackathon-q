import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import tldextract
from rapidfuzz.distance import Levenshtein

from app.schemas.analysis import CheckCode, CheckResult
from app.services.analyses.parsing import ParsedUrl, is_ip_address

CATALOG_DIR = Path(__file__).resolve().parents[2] / "catalog"

# API 명세 4. 위험 점수
SCORES = {
    CheckCode.HTTPS_NOT_USED: 1,
    CheckCode.LOOKALIKE_DOMAIN: 4,
    CheckCode.SUSPICIOUS_URL_STRUCTURE: 1,
    CheckCode.DIRECT_IP_ACCESS: 3,
    CheckCode.EXCESSIVE_REDIRECTS: 1,
    CheckCode.NEW_DOMAIN: 2,
    CheckCode.SUSPICIOUS_TLD: 1,
    CheckCode.BLOCKLIST_MATCH: 10,
    CheckCode.ALLOWLIST_MATCH: 0,
}
MAX_SCORE = 10
# 이 점수 이상이면 피싱 의심 (0~3 안전, 4~6 의도 확인, 7~10 차단)
SUSPICIOUS_MIN_SCORE = 4

# 이 횟수 이상 리디렉션되면 EXCESSIVE_REDIRECTS (최대 허용 횟수 초과는 별도 오류)
EXCESSIVE_REDIRECT_COUNT = 3
LONG_URL_LENGTH = 150
MAX_SUBDOMAIN_DEPTH = 3
# 등록된 지 이 일수 미만이면 NEW_DOMAIN
NEW_DOMAIN_DAYS = 30
SUSPICIOUS_KEYWORDS = (
    "login", "signin", "logon", "verify", "verification", "secure", "account", "update",
    "confirm", "password", "wallet", "banking", "auth", "unlock", "suspend",
)  # fmt: skip

# 등록 가능 도메인 추출: 패키지에 내장된 공개 접미사 목록만 쓰고 실행 중 네트워크 조회를 하지 않는다
_extract = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)

_HOMOGLYPHS = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b"})


@dataclass(frozen=True)
class Brand:
    keyword: str
    domains: tuple[str, ...]


@dataclass(frozen=True)
class UrlCatalog:
    blocklist: tuple[str, ...]
    allowlist: tuple[str, ...]
    shorteners: tuple[str, ...]
    brands: tuple[Brand, ...]
    suspicious_tlds: tuple[str, ...]


def _load_json(name: str):
    with (CATALOG_DIR / name).open(encoding="utf-8") as file:
        return json.load(file)


@lru_cache
def load_catalog() -> UrlCatalog:
    return UrlCatalog(
        blocklist=tuple(_load_json("blocklist.json")["domains"]),
        allowlist=tuple(_load_json("allowlist.json")["domains"]),
        shorteners=tuple(_load_json("url_shorteners.json")["domains"]),
        brands=tuple(
            Brand(keyword=b["keyword"], domains=tuple(b["domains"]))
            for b in _load_json("brands.json")
        ),
        suspicious_tlds=tuple(_load_json("suspicious_tlds.json")["tlds"]),
    )


def matches_domain(host: str, domains: tuple[str, ...]) -> bool:
    return any(host == d or host.endswith(f".{d}") for d in domains)


def registrable_domain(host: str) -> str:
    """naver.com, epost.go.kr 처럼 공개 접미사 바로 앞까지의 도메인. IP 는 그대로 반환한다."""
    if is_ip_address(host):
        return host
    return _extract(host).top_domain_under_public_suffix or host


def _name_labels(host: str) -> list[str]:
    """공개 접미사(.com, .co.kr 등)를 뺀 나머지 라벨. 하위 도메인 깊이·유사 도메인 검사에 쓴다."""
    parts = _extract(host)
    return [label for label in (*parts.subdomain.split("."), parts.domain) if label]


def find_lookalike_brand(host: str, catalog: UrlCatalog) -> str | None:
    """공식 도메인이 아닌데 유명 서비스 이름을 흉내 내면 그 키워드를 반환한다 (URL-005)."""
    if is_ip_address(host) or matches_domain(host, catalog.allowlist):
        return None
    if any(matches_domain(host, brand.domains) for brand in catalog.brands):
        return None

    # 공개 접미사를 뺀 라벨을 하이픈·밑줄 단위로 나눠 비교한다
    tokens = [t for label in _name_labels(host) for t in re.split(r"[-_]", label) if t]
    for brand in catalog.brands:
        keyword = brand.keyword
        for token in tokens:
            plain = token.replace("rn", "m").replace("vv", "w").translate(_HOMOGLYPHS)
            if keyword in plain:
                return keyword
            if len(keyword) >= 5 and Levenshtein.distance(plain, keyword) <= 1:
                return keyword
    return None


def suspicious_tld(host: str, catalog: UrlCatalog) -> str | None:
    """피싱에 자주 쓰이는 TLD 면 그 TLD 를 반환한다. IP·공식 도메인은 검사하지 않는다."""
    if is_ip_address(host) or matches_domain(host, catalog.allowlist):
        return None
    tld = _extract(host).suffix.rsplit(".", 1)[-1]
    return tld if tld in catalog.suspicious_tlds else None


def structure_issue(hops: list[ParsedUrl], catalog: UrlCatalog) -> str | None:
    """URL 길이·하위 도메인·특수 표기·의심 키워드 중 처음 발견된 문제를 반환한다 (URL-006)."""
    final = hops[-1]
    if any(hop.has_userinfo for hop in hops):
        return "주소에 @ 앞부분으로 실제 목적지를 숨기고 있습니다."
    if len(final.url) > LONG_URL_LENGTH:
        return "URL이 지나치게 깁니다."
    if final.is_ip:
        return None
    if "xn--" in final.host:
        return "다른 글자로 위장할 수 있는 국제화 도메인을 사용합니다."
    if len(_name_labels(final.host)) - 1 >= MAX_SUBDOMAIN_DEPTH:
        return "하위 도메인이 지나치게 많습니다."
    if _extract(final.host).domain.count("-") >= 3:
        return "도메인에 하이픈이 지나치게 많습니다."
    if not matches_domain(final.host, catalog.allowlist):
        text = f"{final.host}{final.path_query}".lower()
        if sum(keyword in text for keyword in SUSPICIOUS_KEYWORDS) >= 2:
            return "로그인·인증을 유도하는 단어가 여러 개 포함되어 있습니다."
    return None


def _check(code: CheckCode, detected: bool, message: str) -> CheckResult:
    return CheckResult(
        code=code, detected=detected, score=SCORES[code] if detected else 0, message=message
    )


def _domain_age_message(final: ParsedUrl, allowlisted: bool, age_days: int | None) -> str:
    if final.is_ip:
        return "IP 주소라 도메인 생성일을 확인하지 않습니다."
    if allowlisted:
        return "검증된 공식 도메인이라 생성일을 확인하지 않습니다."
    if age_days is None:
        return "도메인 생성일을 확인하지 못했습니다."
    if age_days < NEW_DOMAIN_DAYS:
        return f"생성된 지 {age_days}일 된 신규 도메인입니다."
    return f"생성된 지 {age_days}일이 지난 도메인입니다."


def evaluate(
    hops: list[ParsedUrl],
    blocked: bool,
    catalog: UrlCatalog,
    unreachable: bool = False,
    domain_age_days: int | None = None,
) -> list[CheckResult]:
    """unreachable: 대상 서버에 접속하지 못해 리디렉션을 끝까지 확인하지 못한 경우.
    domain_age_days: 최종 도메인이 등록된 뒤 지난 일수. 조회하지 않았거나 실패하면 None (#33).
    """
    final = hops[-1]
    redirects = len(hops) - 1
    lookalike = find_lookalike_brand(final.host, catalog)
    structure = structure_issue(hops, catalog)
    direct_ip = any(hop.is_ip for hop in hops)
    allowlisted = matches_domain(final.host, catalog.allowlist)
    tld = suspicious_tld(final.host, catalog)
    new_domain = domain_age_days is not None and domain_age_days < NEW_DOMAIN_DAYS

    return [
        _check(
            CheckCode.BLOCKLIST_MATCH,
            blocked,
            "피싱·악성 URL 차단 목록에 등록된 주소입니다."
            if blocked
            else "차단 목록에 등록된 주소가 아닙니다.",
        ),
        _check(
            CheckCode.HTTPS_NOT_USED,
            final.scheme != "https",
            "HTTPS를 사용하지 않습니다."
            if final.scheme != "https"
            else "HTTPS로 암호화된 연결을 사용합니다.",
        ),
        _check(
            CheckCode.LOOKALIKE_DOMAIN,
            lookalike is not None,
            f"유명 서비스({lookalike})와 유사한 도메인입니다."
            if lookalike
            else "유명 서비스를 흉내 낸 도메인이 발견되지 않았습니다.",
        ),
        _check(
            CheckCode.SUSPICIOUS_URL_STRUCTURE,
            structure is not None,
            f"URL 구조가 일반적이지 않습니다. {structure}"
            if structure
            else "URL 구조가 일반적입니다.",
        ),
        _check(
            CheckCode.DIRECT_IP_ACCESS,
            direct_ip,
            "도메인 없이 IP 주소로 연결됩니다." if direct_ip else "도메인 주소로 연결됩니다.",
        ),
        _check(
            CheckCode.EXCESSIVE_REDIRECTS,
            redirects >= EXCESSIVE_REDIRECT_COUNT,
            f"여러 주소를 거쳐 이동합니다. (리디렉션 {redirects}회)"
            if redirects >= EXCESSIVE_REDIRECT_COUNT
            else "목적지 서버에 접속할 수 없어 리디렉션을 확인하지 못했습니다."
            if unreachable
            else f"리디렉션 {redirects}회로 정상 범위입니다.",
        ),
        _check(
            CheckCode.NEW_DOMAIN,
            new_domain,
            _domain_age_message(final, allowlisted, domain_age_days),
        ),
        _check(
            CheckCode.SUSPICIOUS_TLD,
            tld is not None,
            f"피싱에 자주 쓰이는 최상위 도메인(.{tld})입니다."
            if tld
            else "피싱에 자주 쓰이는 최상위 도메인이 아닙니다.",
        ),
        _check(
            CheckCode.ALLOWLIST_MATCH,
            allowlisted,
            "검증된 공식 도메인입니다."
            if allowlisted
            else "검증된 공식 도메인 목록에 없는 주소입니다.",
        ),
    ]


def total_score(checks: list[CheckResult]) -> int:
    if any(c.code == CheckCode.BLOCKLIST_MATCH and c.detected for c in checks):
        return MAX_SCORE
    return min(MAX_SCORE, sum(c.score for c in checks))
