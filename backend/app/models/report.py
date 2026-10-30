from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    # 동일 분석 결과 중복 신고 방지 (409 REPORT_ALREADY_EXISTS)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), unique=True)
    reason: Mapped[str] = mapped_column(String(30))
    # HTML 로 해석하지 않는 일반 문자열로 저장 (API 명세 6.2)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    review_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
