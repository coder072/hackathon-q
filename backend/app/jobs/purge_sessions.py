"""오래된 분석 세션을 삭제한다 (NFR-007).

앱이 실행 중이면 lifespan 이 1시간마다 실행하고, 수동으로는 python -m app.jobs.purge_sessions
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.analysis_session import AnalysisSession

PURGE_INTERVAL_SECONDS = 60 * 60
logger = logging.getLogger(__name__)


def purge_expired_sessions(now: datetime | None = None) -> int:
    retention = timedelta(hours=get_settings().session_retention_hours)
    cutoff = (now or datetime.now(UTC)) - retention
    with SessionLocal() as db:
        deleted = db.execute(delete(AnalysisSession).where(AnalysisSession.created_at < cutoff))
        db.commit()
    return deleted.rowcount


async def run_periodically() -> None:
    while True:
        try:
            count = await asyncio.to_thread(purge_expired_sessions)
            logger.info("Purged %d old analysis sessions", count)
        except Exception:
            # 테이블이 아직 없거나(마이그레이션 전) DB 오류여도 앱은 계속 동작한다
            logger.exception("Session purge failed")
        await asyncio.sleep(PURGE_INTERVAL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Purged %d old analysis sessions", purge_expired_sessions())
