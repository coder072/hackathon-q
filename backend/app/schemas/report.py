from datetime import datetime
from enum import StrEnum

from pydantic import Field

from app.schemas.common import CamelModel


class ReportReason(StrEnum):
    SUSPICIOUS_LOGIN = "SUSPICIOUS_LOGIN"
    PAYMENT_REQUEST = "PAYMENT_REQUEST"
    IMPERSONATION = "IMPERSONATION"
    MALWARE = "MALWARE"
    OTHER = "OTHER"


class ReportStatus(StrEnum):
    PENDING = "PENDING"
    BLOCKED = "BLOCKED"
    SAFE = "SAFE"


class ReportCreate(CamelModel):
    analysis_id: str
    reason: ReportReason
    description: str | None = Field(default=None, max_length=500)


class ReportCreated(CamelModel):
    report_id: str
    status: ReportStatus
    created_at: datetime
