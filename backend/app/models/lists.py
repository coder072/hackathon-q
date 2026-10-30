from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class BlocklistEntry(Base):
    __tablename__ = "blocklist"
    __table_args__ = (UniqueConstraint("type", "value"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(10))  # DOMAIN | URL
    value: Mapped[str] = mapped_column(String(2048), index=True)
    reason: Mapped[str | None] = mapped_column(String(255))
    source: Mapped[str | None] = mapped_column(String(30))  # USER_REPORT | ADMIN | FEED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AllowlistEntry(Base):
    __tablename__ = "allowlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
