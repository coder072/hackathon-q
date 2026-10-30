from datetime import datetime
from enum import StrEnum

from pydantic import Field

from app.schemas.common import CamelModel


class Verdict(StrEnum):
    SAFE = "SAFE"
    SUSPICIOUS = "SUSPICIOUS"


class RecommendedAction(StrEnum):
    OPEN_ALLOWED = "OPEN_ALLOWED"
    ASK_INTENT = "ASK_INTENT"
    BLOCK = "BLOCK"


class CheckCode(StrEnum):
    HTTPS_NOT_USED = "HTTPS_NOT_USED"
    LOOKALIKE_DOMAIN = "LOOKALIKE_DOMAIN"
    SUSPICIOUS_URL_STRUCTURE = "SUSPICIOUS_URL_STRUCTURE"
    DIRECT_IP_ACCESS = "DIRECT_IP_ACCESS"
    EXCESSIVE_REDIRECTS = "EXCESSIVE_REDIRECTS"
    BLOCKLIST_MATCH = "BLOCKLIST_MATCH"
    ALLOWLIST_MATCH = "ALLOWLIST_MATCH"


class AnalysisRequest(CamelModel):
    # 길이 초과는 URL_TOO_LONG 으로 응답하기 위해 스키마가 아니라 서비스에서 검사한다
    url: str
    client_request_id: str | None = Field(default=None, max_length=100)


class CheckResult(CamelModel):
    code: CheckCode
    detected: bool
    score: int
    message: str


class AnalysisResult(CamelModel):
    analysis_id: str
    verdict: Verdict
    score: int = Field(ge=0, le=10)
    recommended_action: RecommendedAction
    original_url: str
    final_url: str
    display_domain: str
    redirect_count: int
    checks: list[CheckResult]
    analyzed_at: datetime
    expires_at: datetime
