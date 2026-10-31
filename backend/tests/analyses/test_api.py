import asyncio
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx

from app.api.v1.endpoints import analyses
from app.core.config import Settings, get_settings
from app.core.errors import AppError, ErrorCode
from app.core.rate_limit import limiter
from app.db.session import SessionLocal
from app.main import app
from app.models.analysis_session import AnalysisSession


class FakeNet:
    """가짜 DNS(hosts)와 respx 로 가로챈 HTTP 응답(pages). 정하지 않은 페이지는 200 을 돌려준다.

    도메인 등록일(RDAP)은 registered 로 정하고, 정하지 않은 도메인은 조회 실패(None)로 본다.
    """

    def __init__(self, router: respx.Router):
        self.hosts: dict[str, list[str]] = {}
        self.pages: dict[str, tuple[int, str | None]] = {}
        self.error: Exception | None = None
        self.errors: dict[str, Exception] = {}  # URL 별 접속 오류
        self.dns_delay = 0.0
        self.requests: list[httpx.Request] = []
        self.registered: dict[str, datetime] = {}
        self.lookup_delay = 0.0
        self.lookups: list[str] = []
        router.get(url__regex=r".*").mock(side_effect=self._respond)

    def add(self, *names: str) -> None:
        for name in names:
            self.hosts[name] = [f"93.184.216.{len(self.hosts) + 1}"]

    def redirect(self, url: str, location: str, status: int = 302) -> None:
        self.pages[url] = (status, location)

    @property
    def visited(self) -> list[str]:
        # 실제 접속은 IP 로 하므로 Host 헤더로 원래 URL 을 복원한다
        return [
            f"{r.url.scheme}://{r.headers['host']}{r.url.raw_path.decode()}" for r in self.requests
        ]

    async def resolve(self, host: str) -> list[str]:
        if self.dns_delay:
            await asyncio.sleep(self.dns_delay)
        if host not in self.hosts:
            raise AppError(ErrorCode.DNS_RESOLUTION_FAILED)
        return self.hosts[host]

    def register(self, domain: str, days_ago: int) -> None:
        self.registered[domain] = datetime.now(UTC) - timedelta(days=days_ago)

    async def lookup(self, domain: str) -> datetime | None:
        self.lookups.append(domain)
        if self.lookup_delay:
            await asyncio.sleep(self.lookup_delay)
        return self.registered.get(domain)

    def _respond(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.error:
            raise self.error
        if self.visited[-1] in self.errors:
            raise self.errors[self.visited[-1]]
        status, location = self.pages.get(self.visited[-1], (200, None))
        return httpx.Response(status, headers={"location": location} if location else {})


@pytest.fixture
def net(respx_mock):
    fake = FakeNet(respx_mock)
    app.dependency_overrides[analyses.get_resolver] = lambda: fake.resolve
    app.dependency_overrides[analyses.get_domain_lookup] = lambda: fake.lookup
    limiter.reset()
    yield fake
    app.dependency_overrides.clear()


def analyze(client, url, **extra):
    return client.post("/api/v1/analyses", json={"url": url, **extra})


def detected(body):
    return {c["code"] for c in body["data"]["checks"] if c["detected"]}


def test_official_site_is_safe(client, net):
    net.add("www.naver.com")
    r = analyze(client, "HTTPS://WWW.Naver.com:443/?q=1")

    assert r.status_code == 200
    assert r.headers["Cache-Control"] == "no-store"
    data = r.json()["data"]
    assert data["analysisId"].startswith("ana_")
    assert data["verdict"] == "SAFE"
    assert data["recommendedAction"] == "OPEN_ALLOWED"
    assert data["score"] == 0
    assert data["originalUrl"] == "https://www.naver.com/?q=1"
    assert data["displayDomain"] == "www.naver.com"
    assert data["redirectCount"] == 0
    assert data["expiresAt"] > data["analyzedAt"]
    assert detected(r.json()) == {"ALLOWLIST_MATCH"}
    assert len(data["checks"]) == 9
    # 공식 도메인은 등록일을 조회하지 않는다
    assert net.lookups == []
    assert check(r.json(), "NEW_DOMAIN")["message"].startswith("검증된 공식 도메인이라")


def test_connects_to_verified_ip_with_original_host_and_sni(client, net):
    net.add("www.naver.com")
    analyze(client, "https://www.naver.com/")

    (request,) = net.requests
    assert request.url.host == "93.184.216.1"
    assert request.headers["host"] == "www.naver.com"
    assert request.extensions["sni_hostname"] == "www.naver.com"


def test_session_is_stored_for_intent_guidance(client, net):
    net.add("naver-event.com")
    data = analyze(client, "https://naver-event.com/").json()["data"]

    with SessionLocal() as db:
        row = db.get(AnalysisSession, data["analysisId"])
    assert (row.score, row.verdict, row.recommended_action) == (4, "SUSPICIOUS", "ASK_INTENT")


@pytest.mark.parametrize(
    ("url", "score", "verdict", "action"),
    [
        # HTTP(1) + 하이픈 과다(1) + 리디렉션 3회(1) = 3
        ("http://a-b-c-d.com/", 3, "SAFE", "OPEN_ALLOWED"),
        # 유사 도메인(4)
        ("https://naver-event.com/", 4, "SUSPICIOUS", "ASK_INTENT"),
        # 유사 도메인(4) + HTTP(1) + 의심 키워드(1) = 6
        ("http://naver-event.com/login/verify", 6, "SUSPICIOUS", "ASK_INTENT"),
        # 유사 도메인(4) + HTTP(1) + 의심 키워드(1) + 리디렉션 3회(1) = 7
        ("http://kakao-event.com/login/verify", 7, "SUSPICIOUS", "BLOCK"),
    ],
)
def test_score_boundaries(client, net, url, score, verdict, action):
    net.add("a-b-c-d.com", "naver-event.com", "kakao-event.com")
    for host, path in (("a-b-c-d.com", "/"), ("kakao-event.com", "/login/verify")):
        for i in range(3):
            current = f"http://{host}{path}" + (f"?r={i}" if i else "")
            net.redirect(current, f"{path}?r={i + 1}")

    data = analyze(client, url).json()["data"]
    assert (data["score"], data["verdict"], data["recommendedAction"]) == (score, verdict, action)


def test_direct_ip_and_http(client, net):
    r = analyze(client, "http://8.8.8.8/")
    assert r.json()["data"]["score"] == 4
    assert detected(r.json()) == {"DIRECT_IP_ACCESS", "HTTPS_NOT_USED"}


def test_blocklisted_url_is_10_without_network(client, net):
    r = analyze(client, "https://naver-login-security.com/")
    data = r.json()["data"]
    assert (data["score"], data["recommendedAction"]) == (10, "BLOCK")
    assert "BLOCKLIST_MATCH" in detected(r.json())
    assert net.requests == []
    assert net.lookups == []


def check(body, code):
    return next(c for c in body["data"]["checks"] if c["code"] == code)


def test_new_domain_with_suspicious_tld_asks_intent(client, net):
    # URL 모양이 평범한 피싱 주소: 신규 도메인(2) + 위험 TLD(1) + 의심 키워드(1) = 4 (#33)
    net.add("event-gift.shop")
    net.register("event-gift.shop", days_ago=3)
    body = analyze(client, "https://event-gift.shop/login/verify").json()

    assert (body["data"]["score"], body["data"]["recommendedAction"]) == (4, "ASK_INTENT")
    assert detected(body) == {"NEW_DOMAIN", "SUSPICIOUS_TLD", "SUSPICIOUS_URL_STRUCTURE"}
    assert check(body, "NEW_DOMAIN")["message"] == "생성된 지 3일 된 신규 도메인입니다."
    assert check(body, "SUSPICIOUS_TLD")["score"] == 1


def test_old_domain_is_not_new(client, net):
    net.add("www.example.com")
    net.register("example.com", days_ago=400)
    body = analyze(client, "https://www.example.com/").json()

    assert net.lookups == ["example.com"]
    assert body["data"]["score"] == 0
    assert check(body, "NEW_DOMAIN")["message"] == "생성된 지 400일이 지난 도메인입니다."


@pytest.mark.parametrize(("days_ago", "is_new"), [(9, True), (10, False)])
def test_new_domain_threshold_is_10_days(client, net, days_ago, is_new):
    net.add("example.com")
    net.register("example.com", days_ago=days_ago)
    body = analyze(client, "https://example.com/").json()
    assert ("NEW_DOMAIN" in detected(body)) is is_new


def test_unknown_domain_age_adds_no_score(client, net):
    net.add("example.com")
    body = analyze(client, "https://example.com/").json()

    assert body["data"]["score"] == 0
    assert check(body, "NEW_DOMAIN")["message"] == "도메인 생성일을 확인하지 못했습니다."


def test_domain_age_uses_final_domain_after_redirect(client, net):
    net.add("old-site.com", "fresh-site.com")
    net.register("old-site.com", days_ago=1000)
    net.register("fresh-site.com", days_ago=1)
    net.redirect("https://old-site.com/", "https://fresh-site.com/")
    body = analyze(client, "https://old-site.com/").json()

    # 첫 주소로 미리 시작한 조회는 버리고 최종 도메인으로 판정한다
    assert net.lookups[-1] == "fresh-site.com"
    assert "NEW_DOMAIN" in detected(body)


def test_slow_domain_lookup_does_not_block_analysis(client, net):
    net.add("example.com")
    net.lookup_delay = 1
    app.dependency_overrides[get_settings] = lambda: Settings(analysis_timeout_seconds=0.1)
    r = analyze(client, "https://example.com/")

    assert r.status_code == 200
    assert "NEW_DOMAIN" not in detected(r.json())


def test_blocklist_reached_through_redirect(client, net):
    net.add("bit.ly")
    net.redirect("https://bit.ly/abc", "https://kakao-verify-account.com/", 301)
    data = analyze(client, "https://bit.ly/abc").json()["data"]
    assert data["score"] == 10
    assert data["finalUrl"] == "https://kakao-verify-account.com/"
    assert net.visited == ["https://bit.ly/abc"]


def test_shortener_is_judged_by_final_destination(client, net):
    net.add("bit.ly", "www.coupang.com")
    net.redirect("https://bit.ly/x", "https://www.coupang.com/", 301)
    data = analyze(client, "https://bit.ly/x").json()["data"]
    assert data["verdict"] == "SAFE"
    assert data["displayDomain"] == "www.coupang.com"
    assert data["redirectCount"] == 1


def test_shortener_without_destination_fails(client, net):
    net.add("bit.ly")
    r = analyze(client, "https://bit.ly/missing")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "ANALYSIS_FAILED"


@pytest.mark.parametrize(
    ("hosts", "url"),
    [
        ({"localhost": ["127.0.0.1"]}, "http://localhost:8000/"),
        ({}, "http://169.254.169.254/latest/meta-data"),
        ({}, "http://2130706433/"),
        ({}, "http://[::ffff:10.0.0.1]/"),
        ({"mixed.example.com": ["93.184.216.1", "192.168.0.10"]}, "https://mixed.example.com/"),
    ],
)
def test_private_targets_are_blocked(client, net, hosts, url):
    net.hosts = hosts
    r = analyze(client, url)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "PRIVATE_NETWORK_TARGET"
    assert net.requests == []


def test_redirect_to_private_address_is_blocked(client, net):
    net.add("evil.com")
    net.redirect("https://evil.com/", "http://169.254.169.254/")
    r = analyze(client, "https://evil.com/")
    assert r.json()["error"]["code"] == "PRIVATE_NETWORK_TARGET"
    assert net.visited == ["https://evil.com/"]


@pytest.mark.parametrize(("redirects", "status"), [(5, 200), (6, 422)])
def test_redirect_limit(client, net, redirects, status):
    net.add("hop.com")
    for i in range(redirects):
        net.redirect(f"https://hop.com/{i}", f"/{i + 1}")
    r = analyze(client, "https://hop.com/0")
    assert r.status_code == status
    if status == 422:
        assert r.json()["error"]["code"] == "REDIRECT_LIMIT_EXCEEDED"
    else:
        assert r.json()["data"]["redirectCount"] == 5


@pytest.mark.parametrize(
    ("url", "status", "code"),
    [
        ("ftp://example.com/file", 400, "UNSUPPORTED_SCHEME"),
        ("javascript:alert(1)", 400, "UNSUPPORTED_SCHEME"),
        ("naver.com", 400, "INVALID_URL"),
        ("https://exa mple.com/", 400, "INVALID_URL"),
        ("https://example.com/" + "a" * 2048, 400, "URL_TOO_LONG"),
        ("https://no-such-host.example/", 422, "DNS_RESOLUTION_FAILED"),
    ],
)
def test_invalid_input(client, net, url, status, code):
    r = analyze(client, url)
    assert r.status_code == status
    assert r.json()["success"] is False
    assert r.json()["error"]["code"] == code


def test_missing_url_is_invalid_request(client, net):
    r = client.post("/api/v1/analyses", json={})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_REQUEST"


def test_total_timeout(client, net):
    net.add("slow.com")
    net.dns_delay = 1
    app.dependency_overrides[get_settings] = lambda: Settings(analysis_timeout_seconds=0.05)
    r = analyze(client, "https://slow.com/")
    assert r.status_code == 504
    assert r.json()["error"]["code"] == "ANALYSIS_TIMEOUT"


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (httpx.ReadTimeout("slow"), 504, "ANALYSIS_TIMEOUT"),
        (httpx.ConnectError("refused"), 500, "ANALYSIS_FAILED"),
        (RuntimeError("bug"), 500, "ANALYSIS_FAILED"),
    ],
)
def test_failures_are_never_safe(client, net, error, status, code):
    net.add("down.com")
    net.error = error
    r = analyze(client, "https://down.com/")
    assert r.status_code == status
    assert r.json()["success"] is False
    assert r.json()["error"]["code"] == code


def test_client_request_id_returns_same_result(client, net):
    net.add("www.naver.com")
    first = analyze(client, "https://www.naver.com/", clientRequestId="scan-1").json()
    second = analyze(client, "https://www.naver.com/", clientRequestId="scan-1").json()
    assert first["data"]["analysisId"] == second["data"]["analysisId"]
    assert len(net.requests) == 1


def test_rate_limit(client, net, monkeypatch):
    net.add("www.naver.com")
    monkeypatch.setattr(get_settings(), "analysis_rate_limit", "2/minute")
    codes = [analyze(client, "https://www.naver.com/").status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    assert analyze(client, "https://www.naver.com/").json()["error"]["code"] == (
        "RATE_LIMIT_EXCEEDED"
    )


def test_get_returns_stored_result(client, net):
    net.add("www.naver.com")
    created = analyze(client, "http://www.naver.com/?q=1").json()["data"]

    r = client.get(f"/api/v1/analyses/{created['analysisId']}")
    assert r.status_code == 200
    assert r.headers["Cache-Control"] == "no-store"
    assert r.json()["data"] == created
    # 저장된 결과만 돌려주고 다시 접속하지 않는다
    assert len(net.requests) == 1


def test_get_still_works_after_expires_at(client, net):
    net.add("naver-event.com")
    app.dependency_overrides[get_settings] = lambda: Settings(analysis_ttl_minutes=-1)
    created = analyze(client, "https://naver-event.com/").json()["data"]
    assert created["expiresAt"] < created["analyzedAt"]

    r = client.get(f"/api/v1/analyses/{created['analysisId']}")
    assert r.status_code == 200
    assert r.json()["data"]["analysisId"] == created["analysisId"]


@pytest.mark.parametrize(
    "analysis_id",
    [
        "ana_01M678S2BPFJKCZJV985R4Y90B",  # 형식은 맞지만 없는 ID
        "ana_123",
        "req_01M678S0VMFAS1W49KACBTRG38",
        "ana_01M678S2BPFJKCZJV985R4Y90B' OR '1'='1",
    ],
)
def test_get_unknown_or_malformed_id_is_404(client, net, analysis_id):
    r = client.get(f"/api/v1/analyses/{analysis_id}")
    assert r.status_code == 404
    assert r.json()["success"] is False
    assert r.json()["error"]["code"] == "ANALYSIS_NOT_FOUND"


UNREACHABLE = "목적지 서버에 접속할 수 없어 리디렉션을 확인하지 못했습니다."
COUPON_QR = "http://34.223.124.45/event/coupon?ref=" + "a1b2c3d4e5" * 14


@pytest.mark.parametrize("error", [httpx.ConnectTimeout("hang"), httpx.ConnectError("refused")])
def test_unreachable_server_is_judged_by_url_signals(client, net, error):
    # 응답 없는 IP 서버(#26): IP 직접 접속(3) + HTTP(1) + 긴 URL(1) = 5점
    net.error = error
    r = analyze(client, COUPON_QR)

    assert r.status_code == 200
    data = r.json()["data"]
    assert (data["score"], data["recommendedAction"]) == (5, "ASK_INTENT")
    assert detected(r.json()) == {"DIRECT_IP_ACCESS", "HTTPS_NOT_USED", "SUSPICIOUS_URL_STRUCTURE"}
    messages = {c["code"]: c["message"] for c in data["checks"]}
    assert messages["EXCESSIVE_REDIRECTS"] == UNREACHABLE


def test_unreachable_after_redirect_uses_checked_hops(client, net):
    net.add("qr-event.com")
    net.redirect("https://qr-event.com/", "http://5.6.7.8/login")
    net.errors["http://5.6.7.8/login"] = httpx.ConnectError("refused")
    data = analyze(client, "https://qr-event.com/").json()["data"]

    assert data["finalUrl"] == "http://5.6.7.8/login"
    assert data["redirectCount"] == 1
    assert data["score"] == 4  # IP(3) + HTTP(1)


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (httpx.ConnectTimeout("hang"), 504, "ANALYSIS_TIMEOUT"),
        (httpx.ConnectError("refused"), 500, "ANALYSIS_FAILED"),
    ],
)
def test_unreachable_low_score_is_never_safe(client, net, error, status, code):
    # URL 신호가 약하면(4점 미만) 확인하지 못한 링크를 안전으로 판정하지 않는다
    net.add("plain-site.com")
    net.error = error
    r = analyze(client, "https://plain-site.com/")
    assert r.status_code == status
    assert r.json()["error"]["code"] == code


def test_unreachable_shortener_still_fails(client, net):
    net.add("bit.ly")
    net.error = httpx.ConnectError("refused")
    r = analyze(client, "https://bit.ly/abc")
    assert r.json()["error"]["code"] == "ANALYSIS_FAILED"
