from fastapi import APIRouter, Request

from app.api.deps import AppSettings, DbSession
from app.schemas.analysis import AnalysisCreate, AnalysisResult
from app.schemas.common import ApiResponse
from app.services import analysis_service

router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.post("", response_model=ApiResponse[AnalysisResult])
async def create_analysis(
    body: AnalysisCreate, request: Request, db: DbSession, settings: AppSettings
) -> ApiResponse[AnalysisResult]:
    analysis = await analysis_service.create_analysis(db, body, settings)
    return ApiResponse(
        data=analysis_service.to_result(analysis), request_id=request.state.request_id
    )


@router.get("/{analysis_id}", response_model=ApiResponse[AnalysisResult])
def get_analysis(
    analysis_id: str, request: Request, db: DbSession, settings: AppSettings
) -> ApiResponse[AnalysisResult]:
    analysis = analysis_service.get_analysis(db, analysis_id, settings)
    return ApiResponse(
        data=analysis_service.to_result(analysis), request_id=request.state.request_id
    )
