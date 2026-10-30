from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AnalysisSession(Base):
    """URL 분석 결과와 의도 안내 API를 연결하는 세션.

    expires_at(분석 후 20분)까지만 API에서 사용하고, 행 자체는 created_at 기준 24시간 뒤
    정리 작업(app.jobs.purge_sessions)이 삭제한다.
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
