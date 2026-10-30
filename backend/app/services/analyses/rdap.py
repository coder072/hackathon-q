import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

# IANA 가 관리하는 TLD 별 RDAP 서버 목록
BOOTSTRAP_URL = "https://data.iana.org/rdap/dns.json"
# 등록일은 바뀌지 않으므로 성공한 결과를 이 개수까지 메모리에 둔다
CACHE_SIZE = 1024

# 등록 도메인(naver.com)을 받아 등록 시각을 돌려준다. 알 수 없으면 None. 테스트에서는 가짜로 바꾼다
DomainLookup = Callable[[str], Awaitable[datetime | None]]


def registration_date(data: dict) -> datetime | None:
    """RDAP 응답의 events 에서 registration 시각을 꺼낸다."""
    for event in data.get("events", []):
        if event.get("eventAction") == "registration":
            registered = datetime.fromisoformat(event["eventDate"].replace("Z", "+00:00"))
            return registered if registered.tzinfo else registered.replace(tzinfo=UTC)
    return None


class RdapClient:
    """RDAP 로 도메인 등록일을 조회한다 (#33).

    WHOIS 는 레지스트리마다 응답 형식이 달라 JSON 표준인 RDAP 를 쓴다. 요청 대상 서버는
    IANA 목록의 HTTPS 주소뿐이고 사용자 입력으로는 도메인 이름만 바뀐다.
    실패하면 None 을 돌려주고 판정은 계속한다.
    """

    def __init__(self, timeout: float):
        self._timeout = timeout
        self._servers: dict[str, str] | None = None
        self._cache: dict[str, datetime] = {}
        self._lock = asyncio.Lock()

    async def _bootstrap(self, client: httpx.AsyncClient) -> dict[str, str]:
        # 앱 실행 중 한 번만 받는다. 실패하면 다음 조회에서 다시 시도한다
        async with self._lock:
            if self._servers is None:
                response = await client.get(BOOTSTRAP_URL)
                response.raise_for_status()
                servers = {}
                for tlds, urls in response.json()["services"]:
                    url = next((u for u in urls if u.startswith("https://")), None)
                    if url:
                        servers.update({tld.lower(): url.rstrip("/") + "/" for tld in tlds})
                self._servers = servers
            return self._servers

    async def registered_at(self, domain: str) -> datetime | None:
        if domain in self._cache:
            return self._cache[domain]
        registered = await self._lookup(domain)
        if registered is not None and len(self._cache) < CACHE_SIZE:
            self._cache[domain] = registered
        return registered

    async def _lookup(self, domain: str) -> datetime | None:
        try:
            async with (
                asyncio.timeout(self._timeout),
                httpx.AsyncClient(
                    timeout=self._timeout,
                    trust_env=False,
                    headers={"Accept": "application/rdap+json"},
                ) as client,
            ):
                base = (await self._bootstrap(client)).get(domain.rsplit(".", 1)[-1])
                if base is None:
                    return None
                response = await client.get(f"{base}domain/{quote(domain)}")
                if response.status_code != 200:
                    return None
                return registration_date(response.json())
        except (
            TimeoutError,
            httpx.HTTPError,
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
        ) as exc:
            # 도메인은 로그에 남기지 않는다
            logger.info("RDAP lookup failed: %s", type(exc).__name__)
            return None
