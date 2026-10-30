from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analyzer.pipeline import ListSnapshot, run_analysis
from app.core.config import Settings
from app.core.errors import AppError, ErrorCode
from app.core.ids import new_id
from app.models import AllowlistEntry, Analysis, BlocklistEntry
from app.schemas.analysis import AnalysisCreate, AnalysisResult


def _load_lists(db: Session) -> ListSnapshot:
    blocked = db.execute(select(BlocklistEntry.type, BlocklistEntry.value)).all()
    allowed = db.scalars(select(AllowlistEntry.domain)).all()
    return ListSnapshot(
        blocked_domains={v.lower() for t, v in blocked if t == "DOMAIN"},
        blocked_urls={v for t, v in blocked if t == "URL"},
        allowed_domains={d.lower() for d in allowed},
    )


def to_result(a: Analysis) -> AnalysisResult:
    return AnalysisResult(
        analysis_id=a.id,
        verdict=a.verdict,
        score=a.score,
        original_url=a.original_url,
        final_url=a.final_url,
        display_domain=a.display_domain,
        redirect_count=a.redirect_count,
        checks=a.checks,
        analyzed_at=a.analyzed_at,
    )


async def create_analysis(db: Session, req: AnalysisCreate, settings: Settings) -> Analysis:
    # QR-005 중복 분석 요청 방지
    if req.client_request_id:
        existing = db.scalar(
            select(Analysis).where(Analysis.client_request_id == req.client_request_id)
        )
        if existing:
            return existing

    result = await run_analysis(req.url, _load_lists(db), settings)

    analysis = Analysis(
        id=new_id("ana"),
        client_request_id=req.client_request_id,
        source=req.source,
        verdict=result.verdict,
        score=result.score,
        original_url=result.original.url,
        final_url=result.final.url,
        display_domain=result.final.host,
        redirect_count=result.redirect_count,
        checks=[ck.model_dump(mode="json") for ck in result.checks],
        analyzed_at=datetime.now(UTC),
    )
    db.add(analysis)
    db.commit()
    return analysis


def get_analysis(db: Session, analysis_id: str, settings: Settings) -> Analysis:
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise AppError(ErrorCode.ANALYSIS_NOT_FOUND)
    analyzed_at = analysis.analyzed_at
    if analyzed_at.tzinfo is None:  # SQLite 는 tz 정보를 보존하지 않음
        analyzed_at = analyzed_at.replace(tzinfo=UTC)
    if datetime.now(UTC) - analyzed_at > timedelta(hours=settings.analysis_retention_hours):
        raise AppError(ErrorCode.ANALYSIS_NOT_FOUND)
    return analysis


__all__ = ["create_analysis", "get_analysis", "to_result"]
