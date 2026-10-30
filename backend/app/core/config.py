from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "QR Phishing Detector API"
    app_version: str = "1.0.0"
    debug: bool = False

    # 로컬 PostgreSQL (docker compose up db). pytest 는 기본으로 SQLite 를 쓴다
    database_url: str = "postgresql+psycopg://qr:qr@localhost:5433/qr"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    # 분석 요청 제한 (slowapi 형식)
    analysis_rate_limit: str = "30/minute"

    # 분석 세션 행 보관 시간. 앱 실행 중 1시간마다 이보다 오래된 세션을 지운다
    session_retention_hours: int = 24

    # 의도 분류 LLM (4~6점 분석의 POST /intent-guidance 에서만 호출)
    anthropic_api_key: str | None = None
    intent_model: str = "claude-haiku-4-5"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
