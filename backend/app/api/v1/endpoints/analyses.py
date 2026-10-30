import logging
import re
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request, Response

from app.api.deps import AppSettings, DbSession
from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.core.ids import new_id
from app.core.rate_limit import limiter
from app.schemas.analysis import AnalysisRequest, AnalysisResult, RecommendedAction, Verdict
from app.schemas.common import ApiResponse
from app.services.analyses import sessions as analysis_sessions
from app.services.analyses.analyzer import Resolver, analyze_url, resolve_host
from app.services.analyses.rdap import DomainLookup, RdapClient
from app.services.analyses.rules import load_catalog

logger = logging.getLogger(__name__)
router = APIRouter(tags=["analyses"])

# ana_ + ULID(Crockford Base32 26자)
ANALYSIS_ID = re.compile(r"ana_[0-9A-HJKMNP-TV-Z]{26}")


def get_resolver() -> Resolver:
    return resolve_host


@lru_cache
def get_domain_lookup() -> DomainLookup:
    # RDAP 서버 목록을 앱 실행 중 한 번만 받도록 같은 클라이언트를 쓴다
    return RdapClient(get_settings().rdap_timeout_seconds).registered_at


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
    lookup: Annotated[DomainLookup, Depends(get_domain_lookup)],
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
            lookup=lookup,
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


@router.get(
    "/analyses/{analysisId}",
    response_model=ApiResponse[AnalysisResult],
    response_model_by_alias=True,
)
@limiter.limit(lambda: get_settings().analysis_rate_limit)
async def get_analysis(
    analysis_id: Annotated[str, Path(alias="analysisId")],
    request: Request,
    response: Response,
    db: DbSession,
) -> ApiResponse[AnalysisResult]:
    """저장된 분석 결과를 그대로 돌려준다. 다시 분석하거나 외부에 접속하지 않는다.

    expiresAt 은 /intent-guidance 같은 후속 행동의 유효 시간이고, 결과 조회는 기간 제한이 없다.
    """
    response.headers["Cache-Control"] = "no-store"
    # 형식이 맞지 않는 ID 는 DB 를 조회하지 않고 바로 404 로 응답한다
    result = analysis_sessions.get(db, analysis_id) if ANALYSIS_ID.fullmatch(analysis_id) else None
    if result is None:
        raise AppError(ErrorCode.ANALYSIS_NOT_FOUND, "분석 결과를 찾을 수 없습니다.")
    return ApiResponse(data=result, request_id=request.state.request_id)
