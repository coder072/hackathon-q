import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class ServiceDefinition:
    key: str
    name: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class IntentClassification:
    service_key: str | None
    service_name: str | None
    intent_code: str | None
    confidence: float
    additional_keywords: tuple[str, ...]


ACTION_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("DELIVERY_TRACKING", ("배송 조회", "배송", "택배", "운송장", "delivery", "tracking")),
    ("SERVICE_LOGIN", ("로그인", "접속", "sign in", "signin", "log in")),
    ("PAYMENT", ("결제", "납부", "송금", "payment", "pay")),
    ("ACCOUNT_INQUIRY", ("잔액", "계좌 조회", "거래 내역", "내역 조회")),
    ("ORDER_LOOKUP", ("주문 내역", "주문 조회", "주문", "구매 내역")),
    ("CUSTOMER_SUPPORT", ("고객센터", "문의", "상담")),
)

STOP_WORDS = {
    "하려고",
    "하려구",
    "하고",
    "싶어",
    "싶어서",
    "위해",
    "에서",
    "으로",
    "보려고",
    "확인",
}


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold().strip()


@lru_cache
def load_services() -> tuple[ServiceDefinition, ...]:
    path = Path(__file__).resolve().parents[1] / "catalog" / "intent_services.json"
    with path.open(encoding="utf-8") as file:
        raw_services = json.load(file)
    return tuple(
        ServiceDefinition(
            key=item["serviceKey"],
            name=item["serviceName"],
            aliases=tuple(_normalize(alias) for alias in item["aliases"]),
        )
        for item in raw_services
    )


def _find_service(message: str) -> ServiceDefinition | None:
    matches = (
        (len(alias), service)
        for service in load_services()
        for alias in service.aliases
        if alias in message
    )
    return max(matches, default=(0, None), key=lambda item: item[0])[1]


def _find_intent(message: str) -> tuple[str | None, tuple[str, ...]]:
    for code, keywords in ACTION_RULES:
        matched = tuple(keyword for keyword in keywords if keyword in message)
        if matched:
            return code, matched
    return None, ()


def _additional_keywords(
    message: str, service: ServiceDefinition | None, intent_keywords: tuple[str, ...]
) -> tuple[str, ...]:
    excluded = set(intent_keywords) | STOP_WORDS
    if service:
        excluded.update(service.aliases)
    words = re.findall(r"[0-9a-z가-힣]{2,}", message)
    return tuple(dict.fromkeys(word for word in words if word not in excluded))[:5]


def classify_intent(user_message: str) -> IntentClassification:
    """규칙 기반으로 서비스·행동·추가 키워드를 구조화한다.

    URL은 분류 결과에 포함하지 않는다. 공식 URL 추천은 별도의 검증 카탈로그 단계가 맡는다.
    """

    normalized = _normalize(user_message)
    service = _find_service(normalized)
    intent_code, intent_keywords = _find_intent(normalized)
    confidence = 0.0
    if service:
        confidence += 0.45
    if intent_code:
        confidence += 0.45
    keywords = _additional_keywords(normalized, service, intent_keywords)
    if keywords:
        confidence += 0.05

    return IntentClassification(
        service_key=service.key if service else None,
        service_name=service.name if service else None,
        intent_code=intent_code,
        confidence=round(min(confidence, 1.0), 2),
        additional_keywords=keywords,
    )
