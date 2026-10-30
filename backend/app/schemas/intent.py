from enum import StrEnum
from typing import Literal

from pydantic import Field

from app.schemas.common import CamelModel


class GuidanceStatus(StrEnum):
    MATCHED = "MATCHED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    NOT_FOUND = "NOT_FOUND"


class IntentGuidanceRequest(CamelModel):
    analysis_id: str
    # 길이(1~300자)는 INVALID_INTENT_MESSAGE 로 응답하기 위해 엔드포인트에서 검사한다
    user_message: str


class OfficialSiteSuggestion(CamelModel):
    name: str
    url: str
    domain: str
    reason: str
    verified: Literal[True] = True


class IntentAssessment(CamelModel):
    """QR 링크와 사용자 의도를 비교한 판단. 원래 링크를 열어도 된다는 결론은 없다."""

    matches_intent: bool | None  # 서비스를 모르면 null
    explanation: str
    source: Literal["llm", "rules"]


class IntentGuidance(CamelModel):
    analysis_id: str
    guidance_status: GuidanceStatus
    intent_code: str | None
    service_key: str | None
    service_name: str | None
    confidence: float = Field(ge=0, le=1)
    follow_up_question: str | None
    assessment: IntentAssessment
    suggestions: list[OfficialSiteSuggestion] = Field(max_length=3)
