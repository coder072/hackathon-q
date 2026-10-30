from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "QR Phishing Detector API"
    app_version: str = "1.0.0"
    debug: bool = False

    database_url: str = "sqlite:///./data/app.db"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    max_url_length: int = 2048
    max_redirects: int = 5
    analysis_timeout_seconds: float = 5.0
    # 이 횟수를 초과하면 EXCESSIVE_REDIRECTS(+1), max_redirects 초과 시 REDIRECT_LIMIT_EXCEEDED 오류
    excessive_redirect_threshold: int = 2

    # 분석 결과 보관 기간 (API 명세 7. 데이터 보관 정책)
    analysis_retention_hours: int = 24

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
