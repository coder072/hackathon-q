from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AnalysisSession(Base):
    """URL 분석 결과. 행은 영구 보관한다.

    expires_at(분석 후 20분)은 /intent-guidance 같은 후속 행동의 유효 시간이다.
    created_at 기준 24시간 뒤 app.jobs.anonymize_sessions 가 URL 쿼리와 client_request_id 를
    지우고 anonymized_at 을 기록한다.
    """

    __tablename__ = "analysis_sessions"
    __table_args__ = (CheckConstraint("score BETWEEN 0 AND 10", name="ck_analysis_score"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    verdict: Mapped[str] = mapped_column(String(16), nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(32), nullable=False)
    client_request_id: Mapped[str | None] = mapped_column(String(100), index=True)
    # AnalysisResult 의 JSON. 재조회(GET /analyses/{id})와 중복 요청 응답에 그대로 쓴다.
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    anonymized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
