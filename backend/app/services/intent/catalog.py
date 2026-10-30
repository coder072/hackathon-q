import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

CATALOG_PATH = Path(__file__).resolve().parents[2] / "catalog" / "official_sites.json"
ANY_INTENT = "*"
MAX_SUGGESTIONS = 3


@dataclass(frozen=True)
class Intent:
    code: str
    name: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class OfficialSite:
    id: str  # LLM 이 고르는 식별자. URL 은 서버가 이 ID 로 카탈로그에서 꺼낸다
    service_key: str
    intent_codes: tuple[str, ...]
    name: str
    url: str
    reason: str

    @property
    def domain(self) -> str:
        return urlsplit(self.url).hostname or ""


@dataclass(frozen=True)
class Service:
    key: str
    name: str
    aliases: tuple[str, ...]
    brand_keywords: tuple[str, ...]  # URL 분석의 유사 도메인 키워드 (예: naver)
    sites: tuple[OfficialSite, ...]


@dataclass(frozen=True)
class OfficialSiteCatalog:
    intents: tuple[Intent, ...]
    services: tuple[Service, ...]
    intent_defaults: dict[str, tuple[str, ...]]

    @property
    def sites(self) -> tuple[OfficialSite, ...]:
        return tuple(site for service in self.services for site in service.sites)

    def site(self, site_id: str) -> OfficialSite | None:
        return next((s for s in self.sites if s.id == site_id), None)

    def service(self, key: str | None) -> Service | None:
        return next((s for s in self.services if s.key == key), None)

    def intent(self, code: str | None) -> Intent | None:
        return next((i for i in self.intents if i.code == code), None)

    def service_by_brand(self, brand_keyword: str | None) -> Service | None:
        return next((s for s in self.services if brand_keyword in s.brand_keywords), None)

    def sites_for(self, service_key: str, intent_code: str | None) -> list[OfficialSite]:
        """의도에 맞는 페이지를 먼저, 그다음 공식 홈("*"). 의도를 모르면 서비스의 대표 페이지들."""
        service = self.service(service_key)
        if service is None:
            return []
        general = [s for s in service.sites if ANY_INTENT in s.intent_codes]
        if intent_code is None:
            others = [s for s in service.sites if ANY_INTENT not in s.intent_codes]
            return (general + others)[:MAX_SUGGESTIONS]
        exact = [s for s in service.sites if intent_code in s.intent_codes]
        return (exact + general)[:MAX_SUGGESTIONS]

    def sites_for_intent(self, intent_code: str) -> list[OfficialSite]:
        """서비스를 모를 때 그 행동의 대표 서비스들 (예: 배송 조회 → 우체국·CJ대한통운·한진)."""
        picked = [
            self.sites_for(key, intent_code)[0]
            for key in self.intent_defaults.get(intent_code, ())
            if self.sites_for(key, intent_code)
        ]
        return picked[:MAX_SUGGESTIONS]


@lru_cache
def load_official_sites() -> OfficialSiteCatalog:
    """백엔드 저장소의 검증된 공식 사이트 목록. 추천 URL 은 여기서만 나온다 (INT-004)."""
    with CATALOG_PATH.open(encoding="utf-8") as file:
        raw = json.load(file)
    return OfficialSiteCatalog(
        intents=tuple(
            Intent(code=i["code"], name=i["name"], keywords=tuple(i["keywords"]))
            for i in raw["intents"]
        ),
        services=tuple(
            Service(
                key=s["serviceKey"],
                name=s["serviceName"],
                aliases=tuple(s["aliases"]),
                brand_keywords=tuple(s.get("brandKeywords", ())),
                sites=tuple(
                    OfficialSite(
                        id=f"{s['serviceKey']}.{n}",
                        service_key=s["serviceKey"],
                        intent_codes=tuple(site["intentCodes"]),
                        name=site["name"],
                        url=site["url"],
                        reason=site["reason"],
                    )
                    for n, site in enumerate(s["sites"], 1)
                ),
            )
            for s in raw["services"]
        ),
        intent_defaults={k: tuple(v) for k, v in raw.get("intentDefaults", {}).items()},
    )
