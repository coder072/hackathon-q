from dataclasses import dataclass
from typing import Protocol

from app.schemas.intent import GuidanceStatus, OfficialSiteSuggestion
from app.services.intent.assessment import AnalysisContext, Assessment, _object_particle, assess
from app.services.intent.catalog import OfficialSiteCatalog
from app.services.intent.rules import Classification, classify_by_rules


class IntentClassifier(Protocol):
    async def classify(
        self, message: str, context: AnalysisContext | None = None
    ) -> Classification | None: ...


@dataclass(frozen=True)
class Guidance:
    status: GuidanceStatus
    classification: Classification
    follow_up_question: str | None
    suggestions: list[OfficialSiteSuggestion]
    assessment: Assessment


async def classify(
    message: str,
    catalog: OfficialSiteCatalog,
    llm: IntentClassifier | None,
    context: AnalysisContext | None = None,
) -> Classification:
    """LLM 으로 먼저 분류하고, 실패하거나 아무것도 못 찾으면 규칙 기반으로 대체한다."""
    rules = classify_by_rules(message, catalog)
    result = await llm.classify(message, context) if llm else None
    if result is None:
        return rules
    found = (result.service_key is not None) + (result.intent_code is not None)
    found_by_rules = (rules.service_key is not None) + (rules.intent_code is not None)
    return rules if found_by_rules > found else result


def _follow_up(service_name: str | None, intent_name: str | None) -> str:
    if service_name and not intent_name:
        return f"{service_name}에서 로그인, 배송 조회, 결제 중 어떤 일을 하려고 하셨나요?"
    if intent_name and not service_name:
        return f"어느 서비스에서 {intent_name}{_object_particle(intent_name)} 하려고 하셨나요?"
    return "어떤 서비스에서 무엇을 하려고 하셨는지 함께 알려 주세요. 예: 우체국 택배 배송 조회"


async def build_guidance(
    message: str,
    catalog: OfficialSiteCatalog,
    llm: IntentClassifier | None,
    context: AnalysisContext,
) -> Guidance:
    """의도 분류 + QR 링크 판단, 공식 사이트는 카탈로그에서만 찾는다 (INT-003·004, RST-008·010)."""
    result = await classify(message, catalog, llm, context)
    service = catalog.service(result.service_key)
    intent = catalog.intent(result.intent_code)
    # 규칙 기반 결과로 대체된 경우 AI 설명은 다른 분류에 대한 것이므로 쓰지 않는다
    llm_judged = result.source == "llm"
    assessment = assess(
        service,
        result.matches_intent if llm_judged else None,
        result.explanation if llm_judged else None,
        context,
        catalog,
    )

    if service is None or intent is None:
        return Guidance(
            status=GuidanceStatus.NEEDS_CLARIFICATION,
            classification=result,
            follow_up_question=_follow_up(
                service.name if service else None, intent.name if intent else None
            ),
            suggestions=[],
            assessment=assessment,
        )

    sites = catalog.sites_for(service.key, intent.code)
    suggestions = [
        OfficialSiteSuggestion(name=s.name, url=s.url, domain=s.domain, reason=s.reason)
        for s in sites
    ]
    # 후보가 없으면 오류 대신 NOT_FOUND 로 응답하고, 원래 링크는 계속 차단한다
    status = GuidanceStatus.MATCHED if suggestions else GuidanceStatus.NOT_FOUND
    return Guidance(
        status=status,
        classification=result,
        follow_up_question=None,
        suggestions=suggestions,
        assessment=assessment,
    )
