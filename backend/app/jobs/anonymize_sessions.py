"""오래된 분석 세션의 URL 을 익명화한다 (NFR-007). 행은 지우지 않고 영구 보관한다.

created_at 기준 24시간(URL_ANONYMIZE_AFTER_HOURS)이 지난 세션에서 URL 의 쿼리·프래그먼트와
clientRequestId 를 지운다. 도메인·경로·점수·판정·검사 결과는 남아 통계에 쓸 수 있다.

앱이 실행 중이면 lifespan 이 1시간마다 실행하고, 수동으로는 python -m app.jobs.anonymize_sessions
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.analysis_session import AnalysisSession
from app.schemas.analysis import AnalysisResult

RUN_INTERVAL_SECONDS = 60 * 60
logger = logging.getLogger(__name__)


def strip_query(url: str) -> str:
    """쿼리(?...)와 프래그먼트(#...)에는 토큰·전화번호 같은 개인정보가 담길 수 있어 제거한다."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def anonymize_old_sessions(now: datetime | None = None) -> int:
    cutoff = (now or datetime.now(UTC)) - timedelta(hours=get_settings().url_anonymize_after_hours)
    with SessionLocal() as db:
        rows = db.scalars(
            select(AnalysisSession).where(
                AnalysisSession.created_at < cutoff,
                AnalysisSession.anonymized_at.is_(None),
            )
        ).all()
        for row in rows:
            result = AnalysisResult.model_validate_json(row.result_json)
            result.original_url = strip_query(result.original_url)
            result.final_url = strip_query(result.final_url)
            row.result_json = result.model_dump_json(by_alias=True)
            row.client_request_id = None
            row.anonymized_at = now or datetime.now(UTC)
        db.commit()
    return len(rows)


async def run_periodically() -> None:
    while True:
        try:
            count = await asyncio.to_thread(anonymize_old_sessions)
            logger.info("Anonymized %d analysis sessions", count)
        except Exception:
            # 테이블이 아직 없거나(마이그레이션 전) DB 오류여도 앱은 계속 동작한다
            logger.exception("Session anonymization failed")
        await asyncio.sleep(RUN_INTERVAL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Anonymized %d analysis sessions", anonymize_old_sessions())
