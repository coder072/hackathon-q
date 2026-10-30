from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated

import openai
from fastapi import APIRouter, Depends, Request, Response

from app.api.deps import DbSession
from app.api.v1.endpoints.analyses import ANALYSIS_ID
from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.core.rate_limit import limiter
from app.models.analysis_session import AnalysisSession
from app.schemas.analysis import AnalysisResult, RecommendedAction
from app.schemas.common import ApiResponse
from app.schemas.intent import IntentAssessment, IntentGuidance, IntentGuidanceRequest
from app.services.analyses.rules import find_lookalike_brand, load_catalog
from app.services.intent.assessment import AnalysisContext
from app.services.intent.catalog import load_official_sites
from app.services.intent.guidance import IntentClassifier, build_guidance
from app.services.intent.llm import LlmIntentClassifier
from app.services.intent.sensitive import contains_sensitive_data

router = APIRouter(tags=["intent-guidance"])
MAX_MESSAGE_LENGTH = 300


@lru_cache
def get_intent_classifier() -> IntentClassifier | None:
    """API 키가 있으면 OpenAI 분류기, 없으면 None(규칙 기반만 사용)."""
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    client = openai.AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url or None,
        timeout=settings.intent_llm_timeout_seconds,
        max_retries=0,  # 재시도하면 제한 시간을 넘기므로 실패 시 바로 규칙 기반으로 대체한다
    )
    return LlmIntentClassifier(
        client,
        model=settings.intent_model,
        catalog=load_official_sites(),
        timeout=settings.intent_llm_timeout_seconds,
    )


def _ask_intent_session(db: DbSession, analysis_id: str) -> AnalysisSession:
    row = db.get(AnalysisSession, analysis_id) if ANALYSIS_ID.fullmatch(analysis_id) else None
    if row is None:
        raise AppError(ErrorCode.ANALYSIS_NOT_FOUND)
    # SQLite 는 시간대 정보를 저장하지 않으므로 UTC 로 맞춰 비교한다
    expires_at = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        raise AppError(ErrorCode.ANALYSIS_NOT_FOUND)
    if row.recommended_action != RecommendedAction.ASK_INTENT:
        raise AppError(ErrorCode.INTENT_GUIDANCE_NOT_ALLOWED)
    return row


@router.post(
    "/intent-guidance",
    response_model=ApiResponse[IntentGuidance],
    response_model_by_alias=True,
)
@limiter.limit(lambda: get_settings().intent_rate_limit)
async def create_intent_guidance(
    body: IntentGuidanceRequest,
    request: Request,
    response: Response,
    db: DbSession,
    classifier: Annotated[IntentClassifier | None, Depends(get_intent_classifier)],
) -> ApiResponse[IntentGuidance]:
    response.headers["Cache-Control"] = "no-store"
    # API-AC-04: 4~6점(ASK_INTENT)이고 20분이 지나지 않은 분석에서만 허용한다
    session = _ask_intent_session(db, body.analysis_id)

    message = body.user_message.strip()
    if not message or len(message) > MAX_MESSAGE_LENGTH:
        raise AppError(ErrorCode.INVALID_INTENT_MESSAGE)
    # INT-005: 민감정보는 LLM 에 보내지 않는다. 사용자 원문은 저장·로그하지 않는다
    if contains_sensitive_data(message):
        raise AppError(ErrorCode.SENSITIVE_DATA_DETECTED)

    catalog = load_official_sites()
    analysis = AnalysisResult.model_validate_json(session.result_json)
    # QR 도메인이 흉내 낸 서비스 (예: naver.github.io → 네이버). 목적이 모호할 때 안내 대상이 된다
    brand = find_lookalike_brand(analysis.display_domain, load_catalog())
    imitated = catalog.service_by_brand(brand)
    context = AnalysisContext.from_result(analysis, imitated.key if imitated else None)
    guidance = await build_guidance(message, catalog, classifier, context)
    result = guidance.classification
    service = catalog.service(result.service_key)
    return ApiResponse(
        data=IntentGuidance(
            analysis_id=body.analysis_id,
            guidance_status=guidance.status,
            intent_code=result.intent_code,
            service_key=result.service_key,
            service_name=service.name if service else None,
            confidence=result.confidence,
            # 질문은 한 번으로 끝낸다 (#30). 응답 형식 호환을 위해 필드만 남긴다
            follow_up_question=None,
            assessment=IntentAssessment(
                matches_intent=guidance.assessment.matches_intent,
                explanation=guidance.assessment.explanation,
                source=guidance.assessment.source,
            ),
            suggestions=guidance.suggestions,
        ),
        request_id=request.state.request_id,
    )
