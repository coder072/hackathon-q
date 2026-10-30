"""QR 링크 분석 결과와 사용자 의도를 비교한 최종 판단.

AI 가 판단·설명하더라도 서버가 다음을 강제한다.
- 원래 링크를 열어도 된다는 결론은 없다 (4~6점은 항상 차단 유지, RST-006·010).
- QR 도메인이 그 서비스의 공식 도메인이 아니면 '일치'라고 할 수 없다.
- 설명 문구에는 분석한 도메인과 카탈로그 공식 도메인 외의 주소가 들어가지 않는다.
"""

import re
from dataclasses import dataclass

from app.schemas.analysis import AnalysisResult
from app.services.analyses.rules import matches_domain, registrable_domain
from app.services.intent.catalog import OfficialSiteCatalog, Service

MAX_EXPLANATION_LENGTH = 300
# re.ASCII: "naver.github.io로" 처럼 한글이 바로 붙어도 도메인 경계를 정확히 잡는다
_URL = re.compile(r"\b(?:https?|ftp)://[^\s가-힣]+", re.IGNORECASE | re.ASCII)
_DOMAIN = re.compile(
    r"(?<![a-z0-9.-])(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}(?![a-z0-9-])",
    re.IGNORECASE | re.ASCII,
)


@dataclass(frozen=True)
class AnalysisContext:
    """AI 에 넘기는 분석 요약. URL 전체(경로·쿼리)는 넘기지 않는다 (인젝션·개인정보)."""

    domain: str
    score: int
    redirect_count: int
    findings: tuple[str, ...]  # 탐지된 검사의 사용자용 근거 문장
    # QR 도메인이 흉내 낸 것으로 보이는 카탈로그 서비스 키 (예: naver.github.io → naver)
    impersonated_service: str | None = None

    @classmethod
    def from_result(
        cls, result: AnalysisResult, impersonated_service: str | None = None
    ) -> "AnalysisContext":
        return cls(
            domain=result.display_domain,
            score=result.score,
            redirect_count=result.redirect_count,
            findings=tuple(c.message for c in result.checks if c.detected and c.score > 0),
            impersonated_service=impersonated_service,
        )


@dataclass(frozen=True)
class Assessment:
    matches_intent: bool | None  # 서비스를 모르면 None
    explanation: str
    source: str  # "llm" 또는 "rules"


def official_domains(service: Service) -> tuple[str, ...]:
    return tuple(dict.fromkeys(registrable_domain(site.domain) for site in service.sites))


def is_official(domain: str, service: Service) -> bool:
    return matches_domain(domain, official_domains(service))


def sanitize_explanation(
    text: str, context: AnalysisContext, catalog: OfficialSiteCatalog
) -> str | None:
    """URL 은 지우고, 분석한 도메인·공식 도메인이 아닌 주소는 가린다. 남는 내용이 없으면 None."""
    allowed = (
        context.domain,
        *(d for s in catalog.services for d in official_domains(s)),
    )

    def mask(match: re.Match[str]) -> str:
        found = match.group(0).lower()
        return found if matches_domain(found, allowed) else "(주소 생략)"

    cleaned = _DOMAIN.sub(mask, _URL.sub("(주소 생략)", text)).strip()
    return cleaned[:MAX_EXPLANATION_LENGTH] or None


def _object_particle(word: str) -> str:
    """받침이 있으면 '을', 없으면 '를' (한글로 끝나지 않으면 '을(를)')."""
    last = word[-1]
    if not "가" <= last <= "힣":
        return "을(를)"
    return "을" if (ord(last) - ord("가")) % 28 else "를"


def rule_explanation(service: Service | None, matches: bool | None, ctx: AnalysisContext) -> str:
    """AI 를 쓸 수 없거나 AI 판단을 받아들일 수 없을 때의 설명."""
    reason = f" ({ctx.findings[0]})" if ctx.findings else ""
    if service is None:
        return (
            f"이 QR은 {ctx.domain} 주소로 연결되고 피싱 의심 신호가 있어요{reason}. "
            "원래 링크는 열지 마세요."
        )
    name = service.name
    if matches:
        return (
            f"이 QR은 {name} 공식 도메인({ctx.domain})으로 연결되지만 위험 신호가 있어요{reason}. "
            f"안전을 위해 아래 {name} 공식 사이트를 이용하세요."
        )
    return (
        f"{name}{_object_particle(name)} 이용하려 하셨지만, 이 QR은 {name} 공식 주소가 아닌 "
        f"{ctx.domain} 주소로 연결돼요. {name} 사칭이 의심되니 원래 링크는 열지 마세요."
    )


def assess(
    result_service: Service | None,
    llm_matches: bool | None,
    llm_explanation: str | None,
    context: AnalysisContext,
    catalog: OfficialSiteCatalog,
) -> Assessment:
    """AI 판단을 검증해 최종 판단을 만든다. 검증을 통과하지 못하면 규칙 판단으로 대체한다."""
    official = is_official(context.domain, result_service) if result_service else None

    if llm_explanation is not None:
        explanation = sanitize_explanation(llm_explanation, context, catalog)
        # AI 가 공식 도메인이 아닌데 '일치'라고 하면 받아들이지 않는다 (위험을 낮추는 방향 금지)
        trusted = explanation is not None and not (llm_matches and not official)
        if trusted:
            matches = llm_matches if result_service else None
            return Assessment(matches_intent=matches, explanation=explanation, source="llm")

    return Assessment(
        matches_intent=official,
        explanation=rule_explanation(result_service, official, context),
        source="rules",
    )
