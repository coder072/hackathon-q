from datetime import datetime
from enum import StrEnum

from pydantic import Field

from app.schemas.common import CamelModel


class ScanSource(StrEnum):
    CAMERA = "CAMERA"
    IMAGE = "IMAGE"


class Verdict(StrEnum):
    SAFE = "SAFE"
    SUSPICIOUS = "SUSPICIOUS"


class AnalysisCreate(CamelModel):
    # 길이·스킴 검증은 분석 모듈에서 수행해 명세의 오류 코드(URL_TOO_LONG 등)로 응답한다
    url: str = Field(min_length=1)
    source: ScanSource
    client_request_id: str | None = Field(default=None, max_length=100)


class CheckResult(CamelModel):
    code: str
    detected: bool
    score: int
    message: str


class AnalysisResult(CamelModel):
    analysis_id: str
    verdict: Verdict
    score: int = Field(ge=0, le=10)
    original_url: str
    final_url: str
    display_domain: str
    redirect_count: int
    checks: list[CheckResult]
    analyzed_at: datetime
