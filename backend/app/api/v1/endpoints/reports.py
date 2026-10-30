from fastapi import APIRouter, Request, status

from app.api.deps import AppSettings, DbSession
from app.schemas.common import ApiResponse
from app.schemas.report import ReportCreate, ReportCreated
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[ReportCreated])
def create_report(
    body: ReportCreate, request: Request, db: DbSession, settings: AppSettings
) -> ApiResponse[ReportCreated]:
    report = report_service.create_report(db, body, settings)
    return ApiResponse(
        data=ReportCreated(report_id=report.id, status=report.status, created_at=report.created_at),
        request_id=request.state.request_id,
    )
