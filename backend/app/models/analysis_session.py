from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AnalysisSession(Base):
    """URL 분석 결과와 의도 안내 API를 연결하는 단기 세션."""

    __tablename__ = "analysis_sessions"
    __table_args__ = (CheckConstraint("score BETWEEN 0 AND 10", name="ck_analysis_score"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
