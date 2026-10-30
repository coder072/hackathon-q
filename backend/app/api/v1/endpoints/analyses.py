import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.api.deps import AppSettings, DbSession
from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.core.ids import new_id
from app.core.rate_limit import limiter
from app.schemas.analysis import AnalysisRequest, AnalysisResult, RecommendedAction, Verdict
from app.schemas.common import ApiResponse
from app.services.analyses import sessions as analysis_sessions
from app.services.analyses.analyzer import Resolver, analyze_url, resolve_host
from app.services.analyses.rules import load_catalog

logger = logging.getLogger(__name__)
router = APIRouter(tags=["analyses"])


def get_resolver() -> Resolver:
    return resolve_host


def decide(score: int) -> tuple[Verdict, RecommendedAction]:
    """RST-001: 0~3 안전, 4~6 의도 확인, 7~10 차단."""
    if score <= 3:
        return Verdict.SAFE, RecommendedAction.OPEN_ALLOWED
    if score <= 6:
        return Verdict.SUSPICIOUS, RecommendedAction.ASK_INTENT
    return Verdict.SUSPICIOUS, RecommendedAction.BLOCK


@router.post(
    "/analyses",
    response_model=ApiResponse[AnalysisResult],
    response_model_by_alias=True,
)
@limiter.limit(lambda: get_settings().analysis_rate_limit)
async def create_analysis(
    body: AnalysisRequest,
    request: Request,
    response: Response,
    db: DbSession,
    settings: AppSettings,
    resolve: Annotated[Resolver, Depends(get_resolver)],
) -> ApiResponse[AnalysisResult]:
    response.headers["Cache-Control"] = "no-store"
    request_id = request.state.request_id

    # QR-004: 같은 clientRequestId 로 다시 요청하면 분석하지 않고 기존 결과를 돌려준다
    if body.client_request_id:
        cached = analysis_sessions.find_by_client_request_id(db, body.client_request_id)
        if cached:
            return ApiResponse(data=cached, request_id=request_id)

    try:
        outcome = await analyze_url(
            body.url,
            resolve=resolve,
            catalog=load_catalog(),
            max_redirects=settings.max_redirects,
            timeout=settings.analysis_timeout_seconds,
        )
    except AppError:
        raise
    except Exception as exc:
        # 분석 실패는 절대 안전으로 처리하지 않는다 (API-AC-03). URL 은 로그에 남기지 않는다.
        logger.exception("URL analysis failed rid=%s", request_id)
        raise AppError(ErrorCode.ANALYSIS_FAILED) from exc

    verdict, action = decide(outcome.score)
    analyzed_at = datetime.now(UTC)
    result = AnalysisResult(
        analysis_id=new_id("ana"),
        verdict=verdict,
        score=outcome.score,
        recommended_action=action,
        original_url=outcome.original.url,
        final_url=outcome.final.url,
        display_domain=outcome.final.host,
        redirect_count=len(outcome.hops) - 1,
        checks=outcome.checks,
        analyzed_at=analyzed_at,
        expires_at=analyzed_at + timedelta(minutes=settings.analysis_ttl_minutes),
    )
    analysis_sessions.save(db, result, body.client_request_id)
    return ApiResponse(data=result, request_id=request_id)
