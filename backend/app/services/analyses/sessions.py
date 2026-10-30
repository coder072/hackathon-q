from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis_session import AnalysisSession
from app.schemas.analysis import AnalysisResult


def find_by_client_request_id(db: Session, client_request_id: str) -> AnalysisResult | None:
    row = db.scalars(
        select(AnalysisSession).where(
            AnalysisSession.client_request_id == client_request_id,
            AnalysisSession.expires_at > datetime.now(UTC),
        )
    ).first()
    return AnalysisResult.model_validate_json(row.result_json) if row else None


def save(db: Session, result: AnalysisResult, client_request_id: str | None) -> None:
    # 오래된 세션은 app.jobs.purge_sessions 가 24시간 뒤 지운다
    db.add(
        AnalysisSession(
            id=result.analysis_id,
            score=result.score,
            recommended_action=result.recommended_action,
            verdict=result.verdict,
            expires_at=result.expires_at,
            client_request_id=client_request_id,
            result_json=result.model_dump_json(by_alias=True),
        )
    )
    db.commit()
