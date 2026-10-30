from dataclasses import dataclass
from typing import Protocol

from app.schemas.intent import GuidanceStatus, OfficialSiteSuggestion
from app.services.intent.assessment import AnalysisContext, Assessment, assess
from app.services.intent.catalog import MAX_SUGGESTIONS, OfficialSite, OfficialSiteCatalog
from app.services.intent.rules import Classification, classify_by_rules


class IntentClassifier(Protocol):
    async def classify(
        self, message: str, context: AnalysisContext | None = None
    ) -> Classification | None: ...


@dataclass(frozen=True)
class Guidance:
    status: GuidanceStatus
    classification: Classification
    suggestions: list[OfficialSiteSuggestion]
    assessment: Assessment


async def classify(
    message: str,
    catalog: OfficialSiteCatalog,
    llm: IntentClassifier | None,
    context: AnalysisContext | None = None,
) -> Classification:
    """LLM 으로 먼저 판단하고, 실패하면 규칙 기반으로 대체한다."""
    result = await llm.classify(message, context) if llm else None
    return result if result is not None else classify_by_rules(message, catalog)


def _pick_sites(
    result: Classification, catalog: OfficialSiteCatalog, context: AnalysisContext
) -> list[OfficialSite]:
    """질문 한 번으로 끝내기 위해 가장 알맞은 공식 사이트를 고른다 (#30).

    1. LLM 이 고른 사이트 (카탈로그에 있는 ID 만)
    2. 서비스를 알면 그 서비스의 의도 페이지·공식 홈
    3. 행동만 알면 그 행동의 대표 서비스들 (예: 배송 조회 → 우체국·CJ대한통운·한진)
    4. 둘 다 모르면 QR 도메인이 흉내 낸 서비스
    """
    llm_sites = [s for s in map(catalog.site, result.site_ids) if s is not None]
    if llm_sites:
        return llm_sites[:MAX_SUGGESTIONS]
    if result.service_key:
        return catalog.sites_for(result.service_key, result.intent_code)
    if result.intent_code:
        return catalog.sites_for_intent(result.intent_code)
    if context.impersonated_service:
        return catalog.sites_for(context.impersonated_service, None)
    return []


async def build_guidance(
    message: str,
    catalog: OfficialSiteCatalog,
    llm: IntentClassifier | None,
    context: AnalysisContext,
) -> Guidance:
    """사용자 목적 한 번으로 공식 사이트를 안내한다. 추가 질문은 하지 않는다 (INT-003·004)."""
    result = await classify(message, catalog, llm, context)
    service = catalog.service(result.service_key)
    llm_judged = result.source == "llm"
    assessment = assess(
        service,
        result.matches_intent if llm_judged else None,
        result.explanation if llm_judged else None,
        context,
        catalog,
    )

    suggestions = [
        OfficialSiteSuggestion(name=s.name, url=s.url, domain=s.domain, reason=s.reason)
        for s in _pick_sites(result, catalog, context)
    ]
    # 후보가 없으면 오류 대신 NOT_FOUND 로 응답하고, 원래 링크는 계속 차단한다
    status = GuidanceStatus.MATCHED if suggestions else GuidanceStatus.NOT_FOUND
    return Guidance(
        status=status, classification=result, suggestions=suggestions, assessment=assessment
    )
