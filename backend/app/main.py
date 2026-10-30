import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.handlers import register_exception_handlers
from app.core.middleware import RequestIdMiddleware
from app.core.rate_limit import limiter
from app.jobs.anonymize_sessions import run_periodically

settings = get_settings()
logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    anonymize_task = asyncio.create_task(run_periodically())
    yield
    anonymize_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await anonymize_task


# 스키마는 Alembic 마이그레이션으로 관리한다 (실행 전 alembic upgrade head)
app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
app.state.limiter = limiter

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "Accept", "X-Request-ID", "Authorization"],
    expose_headers=["X-Request-ID"],
)
register_exception_handlers(app)
app.include_router(api_router)
