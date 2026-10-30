from enum import StrEnum

from pydantic import Field

from app.schemas.common import CamelModel


class GuidanceStatus(StrEnum):
    MATCHED = "MATCHED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    NOT_FOUND = "NOT_FOUND"


class IntentGuidanceRequest(CamelModel):
    analysis_id: str
    user_message: str


class OfficialSiteSuggestion(CamelModel):
    name: str
    url: str
    domain: str
    reason: str
    verified: bool = True


class IntentGuidance(CamelModel):
    analysis_id: str
    guidance_status: GuidanceStatus
    intent_code: str | None
    service_key: str | None
    service_name: str | None
    confidence: float = Field(ge=0, le=1)
    follow_up_question: str | None
    additional_keywords: list[str] = Field(default_factory=list)
    suggestions: list[OfficialSiteSuggestion] = Field(default_factory=list, max_length=3)
