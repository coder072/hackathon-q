import re
from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import DbSession
from app.core.errors import AppError, ErrorCode
from app.models.analysis_session import AnalysisSession
from app.schemas.common import ApiResponse
from app.schemas.intent import GuidanceStatus, IntentGuidance, IntentGuidanceRequest
from app.services.intent_classifier import classify_intent

router = APIRouter(tags=["intent-guidance"])

SENSITIVE_PATTERNS = (
    re.compile(r"\b\d{6}-?[1-4]\d{6}\b"),
    re.compile(r"(?:인증번호|otp)\s*[:=]?\s*\d{6}\b", re.IGNORECASE),
    re.compile(r"(?:계좌번호|account)\s*[:=]?\s*\d[\d-]{7,18}\b", re.IGNORECASE),
    re.compile(r"(?:비밀번호|패스워드|password)\s*[:=]\s*\S{4,}", re.IGNORECASE),
)


def _is_expired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= datetime.now(UTC)


def _get_analysis(db: Session, analysis_id: str) -> AnalysisSession:
    analysis = db.get(AnalysisSession, analysis_id)
    if analysis is None or _is_expired(analysis.expires_at):
        raise AppError(ErrorCode.ANALYSIS_NOT_FOUND)
    if analysis.recommended_action != "ASK_INTENT" or not 4 <= analysis.score <= 6:
        raise AppError(ErrorCode.INTENT_GUIDANCE_NOT_ALLOWED)
    return analysis


def _validate_message(user_message: str) -> str:
    message = user_message.strip()
    if not message or len(message) > 300:
        raise AppError(ErrorCode.INVALID_INTENT_MESSAGE)
    if any(pattern.search(message) for pattern in SENSITIVE_PATTERNS):
        raise AppError(ErrorCode.SENSITIVE_DATA_DETECTED)
    return message


def _clarification_question(service_name: str | None, intent_code: str | None) -> str:
    if service_name and not intent_code:
        return f"{service_name}에서 로그인, 조회, 결제 중 어떤 작업을 하려는지 알려 주세요."
    if intent_code and not service_name:
        return "어느 서비스에서 그 작업을 하려는지 서비스 이름을 알려 주세요."
    return "어떤 서비스에서 무엇을 하려는지 함께 알려 주세요."


@router.post(
    "/intent-guidance",
    response_model=ApiResponse[IntentGuidance],
    response_model_by_alias=True,
)
def create_intent_guidance(
    body: IntentGuidanceRequest,
    request: Request,
    response: Response,
    db: DbSession,
) -> ApiResponse[IntentGuidance]:
    _get_analysis(db, body.analysis_id)
    message = _validate_message(body.user_message)
    classification = classify_intent(message)

    complete = bool(classification.service_key and classification.intent_code)
    status = GuidanceStatus.NOT_FOUND if complete else GuidanceStatus.NEEDS_CLARIFICATION
    follow_up = (
        None
        if complete
        else _clarification_question(classification.service_name, classification.intent_code)
    )

    # 자연어 원문은 저장·로그하지 않는다. 공식 URL 추천(INT-003)은 검증 카탈로그가
    # 준비될 때 별도 단계로 연결하며, 현재는 URL을 생성하지 않고 차단 상태를 유지한다.
    response.headers["Cache-Control"] = "no-store"
    return ApiResponse(
        data=IntentGuidance(
            analysis_id=body.analysis_id,
            guidance_status=status,
            intent_code=classification.intent_code,
            service_key=classification.service_key,
            service_name=classification.service_name,
            confidence=classification.confidence,
            follow_up_question=follow_up,
            additional_keywords=list(classification.additional_keywords),
            suggestions=[],
        ),
        request_id=request.state.request_id,
    )
