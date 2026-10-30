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

    # URL 분석 (API 명세 보안 정책)
    analysis_rate_limit: str = "30/minute"  # slowapi 형식
    analysis_ttl_minutes: int = 20
    analysis_timeout_seconds: float = 5.0
    max_redirects: int = 5

    # 분석 세션은 영구 보관하고, 이 시간이 지나면 URL 쿼리·clientRequestId 를 지운다
    url_anonymize_after_hours: int = 24

    # 의도 분류 LLM (4~6점 분석의 POST /intent-guidance 에서만 호출). 키가 없으면 규칙 기반만 쓴다
    openai_api_key: str | None = None
    # OpenAI 호환 게이트웨이 주소. 기본은 팩트챗, 비우면 OpenAI 를 직접 호출한다
    openai_base_url: str | None = "https://factchat-cloud.mindlogic.ai/v1/gateway"
    # 팩트챗의 OpenAI 모델. 실측 평균 1.7초(최대 2.2초), 모르는 서비스는 추측하지 않는다
    intent_model: str = "gpt-5.4"
    intent_llm_timeout_seconds: float = 5.0
    intent_rate_limit: str = "10/minute"  # slowapi 형식

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
