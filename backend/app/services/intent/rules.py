import unicodedata
from dataclasses import dataclass

from app.services.intent.catalog import OfficialSiteCatalog


@dataclass(frozen=True)
class Classification:
    service_key: str | None
    intent_code: str | None
    confidence: float
    source: str  # "llm" 또는 "rules"
    # LLM 이 QR 링크와 사용자 의도를 비교한 판단. 규칙 기반은 비워 두고 서버가 채운다
    matches_intent: bool | None = None
    explanation: str | None = None


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold().strip()


def classify_by_rules(message: str, catalog: OfficialSiteCatalog) -> Classification:
    """서비스 별칭·행동 키워드로 분류한다. LLM 을 쓸 수 없을 때의 대체 분류기."""
    text = _normalize(message)

    # 가장 긴 별칭이 맞는 서비스를 고른다 ("우체국택배" > "우체국")
    matches = [
        (len(alias), service.key)
        for service in catalog.services
        for alias in service.aliases
        if _normalize(alias) in text
    ]
    service_key = max(matches)[1] if matches else None
    intent_code = next(
        (i.code for i in catalog.intents if any(_normalize(k) in text for k in i.keywords)),
        None,
    )
    confidence = 0.45 * (service_key is not None) + 0.45 * (intent_code is not None)
    return Classification(service_key, intent_code, round(confidence, 2), source="rules")
