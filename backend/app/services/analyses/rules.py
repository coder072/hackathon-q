import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

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
    CheckCode.BLOCKLIST_MATCH: 10,
    CheckCode.ALLOWLIST_MATCH: 0,
}
MAX_SCORE = 10

# 이 횟수 이상 리디렉션되면 EXCESSIVE_REDIRECTS (최대 허용 횟수 초과는 별도 오류)
EXCESSIVE_REDIRECT_COUNT = 3
LONG_URL_LENGTH = 150
MAX_SUBDOMAIN_DEPTH = 3
SUSPICIOUS_KEYWORDS = (
    "login", "signin", "logon", "verify", "verification", "secure", "account", "update",
    "confirm", "password", "wallet", "banking", "auth", "unlock", "suspend",
)  # fmt: skip

# 등록 가능 도메인 계산용 2단계 공개 접미사 (공개 접미사 목록의 축약판)
SECOND_LEVEL_SUFFIXES = frozenset(
    {
        "co.kr", "or.kr", "go.kr", "ac.kr", "ne.kr", "re.kr", "pe.kr", "ms.kr", "hs.kr",
        "co.uk", "org.uk", "ac.uk", "co.jp", "ne.jp", "or.jp", "com.au", "com.cn", "com.br",
    }
)  # fmt: skip

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
    )


def matches_domain(host: str, domains: tuple[str, ...]) -> bool:
    return any(host == d or host.endswith(f".{d}") for d in domains)


def registrable_domain(host: str) -> str:
    if is_ip_address(host):
        return host
    labels = host.split(".")
    size = 3 if ".".join(labels[-2:]) in SECOND_LEVEL_SUFFIXES else 2
    return ".".join(labels[-size:])


def _edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def find_lookalike_brand(host: str, catalog: UrlCatalog) -> str | None:
    """공식 도메인이 아닌데 유명 서비스 이름을 흉내 내면 그 키워드를 반환한다 (URL-005)."""
    if is_ip_address(host) or matches_domain(host, catalog.allowlist):
        return None
    if any(matches_domain(host, brand.domains) for brand in catalog.brands):
        return None

    # 최상위 도메인을 제외한 라벨을 하이픈·밑줄 단위로 나눠 비교한다
    tokens = [t for t in re.split(r"[.\-_]", ".".join(host.split(".")[:-1])) if t]
    for brand in catalog.brands:
        keyword = brand.keyword
        for token in tokens:
            plain = token.replace("rn", "m").replace("vv", "w").translate(_HOMOGLYPHS)
            if keyword in plain:
                return keyword
            if len(keyword) >= 5 and _edit_distance(plain, keyword) <= 1:
                return keyword
    return None


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
    subdomain_depth = final.host.count(".") - registrable_domain(final.host).count(".")
    if subdomain_depth >= MAX_SUBDOMAIN_DEPTH:
        return "하위 도메인이 지나치게 많습니다."
    if registrable_domain(final.host).split(".")[0].count("-") >= 3:
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


def evaluate(hops: list[ParsedUrl], blocked: bool, catalog: UrlCatalog) -> list[CheckResult]:
    final = hops[-1]
    redirects = len(hops) - 1
    lookalike = find_lookalike_brand(final.host, catalog)
    structure = structure_issue(hops, catalog)
    direct_ip = any(hop.is_ip for hop in hops)
    allowlisted = matches_domain(final.host, catalog.allowlist)

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
            else f"리디렉션 {redirects}회로 정상 범위입니다.",
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
