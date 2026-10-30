from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    client_request_id: Mapped[str | None] = mapped_column(String(100), index=True)
    source: Mapped[str] = mapped_column(String(10))
    verdict: Mapped[str] = mapped_column(String(20))
    score: Mapped[int] = mapped_column(Integer)
    original_url: Mapped[str] = mapped_column(String(2048))
    final_url: Mapped[str] = mapped_column(String(2048))
    display_domain: Mapped[str] = mapped_column(String(255), index=True)
    redirect_count: Mapped[int] = mapped_column(Integer, default=0)
    checks: Mapped[list[dict]] = mapped_column(JSON, default=list)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
