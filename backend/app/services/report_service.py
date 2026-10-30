from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError, ErrorCode
from app.core.ids import new_id
from app.models import Report
from app.schemas.report import ReportCreate, ReportStatus
from app.services.analysis_service import get_analysis


def create_report(db: Session, req: ReportCreate, settings: Settings) -> Report:
    get_analysis(db, req.analysis_id, settings)

    if db.scalar(select(Report.id).where(Report.analysis_id == req.analysis_id)):
        raise AppError(ErrorCode.REPORT_ALREADY_EXISTS)

    report = Report(
        id=new_id("rpt"),
        analysis_id=req.analysis_id,
        reason=req.reason,
        description=req.description,
        status=ReportStatus.PENDING,
        created_at=datetime.now(UTC),
    )
    db.add(report)
    db.commit()
    return report
