import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

CATALOG_PATH = Path(__file__).resolve().parents[2] / "catalog" / "official_sites.json"
ANY_INTENT = "*"


@dataclass(frozen=True)
class Intent:
    code: str
    name: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class OfficialSite:
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
    sites: tuple[OfficialSite, ...]


@dataclass(frozen=True)
class OfficialSiteCatalog:
    intents: tuple[Intent, ...]
    services: tuple[Service, ...]

    def service(self, key: str | None) -> Service | None:
        return next((s for s in self.services if s.key == key), None)

    def intent(self, code: str | None) -> Intent | None:
        return next((i for i in self.intents if i.code == code), None)

    def sites_for(self, service_key: str, intent_code: str, limit: int = 3) -> list[OfficialSite]:
        """의도에 딱 맞는 페이지를 먼저, 그다음 공식 홈페이지("*")를 최대 limit 개 돌려준다."""
        service = self.service(service_key)
        if service is None:
            return []
        exact = [s for s in service.sites if intent_code in s.intent_codes]
        general = [s for s in service.sites if ANY_INTENT in s.intent_codes]
        return (exact + general)[:limit]


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
                sites=tuple(
                    OfficialSite(
                        intent_codes=tuple(site["intentCodes"]),
                        name=site["name"],
                        url=site["url"],
                        reason=site["reason"],
                    )
                    for site in s["sites"]
                ),
            )
            for s in raw["services"]
        ),
    )
