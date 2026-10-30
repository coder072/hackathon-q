from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis_session import AnalysisSession
from app.schemas.analysis import AnalysisResult


def get(db: Session, analysis_id: str) -> AnalysisResult | None:
    """저장된 분석 결과. 만료(expiresAt)와 관계없이 조회한다."""
    row = db.get(AnalysisSession, analysis_id)
    return AnalysisResult.model_validate_json(row.result_json) if row else None


def find_by_client_request_id(db: Session, client_request_id: str) -> AnalysisResult | None:
    row = db.scalars(
        select(AnalysisSession).where(
            AnalysisSession.client_request_id == client_request_id,
            AnalysisSession.expires_at > datetime.now(UTC),
        )
    ).first()
    return AnalysisResult.model_validate_json(row.result_json) if row else None


def save(db: Session, result: AnalysisResult, client_request_id: str | None) -> None:
    # 행은 영구 보관하고, 24시간 뒤 app.jobs.anonymize_sessions 가 URL 쿼리를 지운다
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
