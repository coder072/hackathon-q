from fastapi import APIRouter

from app.api.v1.endpoints import analyses, health, reports

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(analyses.router)
api_router.include_router(reports.router)
# TODO(MVP 이후): admin 라우터 (/admin/reports, /admin/blocklist, /admin/allowlist)
