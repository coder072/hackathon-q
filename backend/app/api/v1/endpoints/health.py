from datetime import UTC, datetime

from fastapi import APIRouter, Request

from app.api.deps import AppSettings
from app.schemas.common import ApiResponse
from app.schemas.health import HealthStatus

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse[HealthStatus], response_model_by_alias=True)
def health(request: Request, settings: AppSettings) -> ApiResponse[HealthStatus]:
    return ApiResponse(
        data=HealthStatus(status="UP", version=settings.app_version, timestamp=datetime.now(UTC)),
        request_id=request.state.request_id,
    )
