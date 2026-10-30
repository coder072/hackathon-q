import asyncio
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select

from app.api.v1.endpoints import analyses
from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.main import app
from app.models.analysis_session import AnalysisSession
from app.services.analyses.analyzer import HopResponse
from app.services.analyses.parsing import ParsedUrl

PUBLIC_IP = "93.184.216.34"


class FakeProbe:
    """DNS 응답(hosts)과 URL별 응답(routes)을 미리 정해 두는 가짜 네트워크."""

    def __init__(self, hosts=None, routes=None, delay=0.0, error=None):
        self.hosts = hosts or {}
        self.routes = routes or {}
        self.delay = delay
        self.error = error
        self.fetched: list[str] = []

    async def resolve(self, host):
        if host not in self.hosts:
            from app.core.errors import AppError, ErrorCode

            raise AppError(ErrorCode.DNS_RESOLUTION_FAILED)
        return self.hosts[host]

    async def fetch(self, url: ParsedUrl, ip, timeout):
        self.fetched.append(url.url)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        status, location = self.routes.get(url.url, (200, None))
        return HopResponse(status, location)


@pytest.fixture
def probe():
    fake = FakeProbe()
    app.dependency_overrides[analyses.get_url_probe] = lambda: fake
    analyses.rate_limiter.clear()
    yield fake
    app.dependency_overrides.clear()


def analyze(client, url, **extra):
    return client.post("/api/v1/analyses", json={"url": url, **extra})


def detected(body):
    return {c["code"] for c in body["data"]["checks"] if c["detected"]}


def test_official_site_is_safe(client, probe):
    probe.hosts = {"www.naver.com": [PUBLIC_IP]}
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
    assert len(data["checks"]) == 7


def test_session_is_stored_for_intent_guidance(client, probe):
    probe.hosts = {"naver-event.com": [PUBLIC_IP]}
    data = analyze(client, "https://naver-event.com/").json()["data"]

    with SessionLocal() as db:
        row = db.get(AnalysisSession, data["analysisId"])
    assert row.score == 4
    assert row.recommended_action == "ASK_INTENT"


@pytest.mark.parametrize(
    ("url", "score", "verdict", "action"),
    [
        # HTTP(1) + 하이픈 과다(1) + 리디렉션 3회(1) = 3
        ("http://a-b-c-d.com/", 3, "SAFE", "OPEN_ALLOWED"),
        # 유사 도메인(4)
        ("https://naver-event.com/", 4, "SUSPICIOUS", "ASK_INTENT"),
        # 유사 도메인(4) + HTTP(1) + 의심 키워드(1) = 6
        ("http://naver-event.com/login/verify", 6, "SUSPICIOUS", "ASK_INTENT"),
        # 유사 도메인(4) + IP 없음, HTTP(1) + 의심 키워드(1) + 리디렉션 3회(1) = 7
        ("http://kakao-event.com/login/verify", 7, "SUSPICIOUS", "BLOCK"),
    ],
)
def test_score_boundaries(client, probe, url, score, verdict, action):
    probe.hosts = {h: [PUBLIC_IP] for h in ("a-b-c-d.com", "naver-event.com", "kakao-event.com")}
    for host, path in (("a-b-c-d.com", "/"), ("kakao-event.com", "/login/verify")):
        probe.routes |= {
            f"http://{host}{path}": (302, f"{path}?r=1"),
            f"http://{host}{path}?r=1": (302, f"{path}?r=2"),
            f"http://{host}{path}?r=2": (302, f"{path}?r=3"),
        }

    data = analyze(client, url).json()["data"]
    assert (data["score"], data["verdict"], data["recommendedAction"]) == (score, verdict, action)


def test_direct_ip_and_http(client, probe):
    r = analyze(client, "http://8.8.8.8/")
    assert r.json()["data"]["score"] == 4
    assert detected(r.json()) == {"DIRECT_IP_ACCESS", "HTTPS_NOT_USED"}


def test_blocklisted_url_is_10_without_network(client, probe):
    r = analyze(client, "https://naver-login-security.com/")
    data = r.json()["data"]
    assert data["score"] == 10
    assert data["recommendedAction"] == "BLOCK"
    assert "BLOCKLIST_MATCH" in detected(r.json())
    assert probe.fetched == []


def test_blocklist_reached_through_redirect(client, probe):
    probe.hosts = {"bit.ly": [PUBLIC_IP]}
    probe.routes = {"https://bit.ly/abc": (301, "https://kakao-verify-account.com/")}
    data = analyze(client, "https://bit.ly/abc").json()["data"]
    assert data["score"] == 10
    assert data["finalUrl"] == "https://kakao-verify-account.com/"
    assert probe.fetched == ["https://bit.ly/abc"]


def test_shortener_is_judged_by_final_destination(client, probe):
    probe.hosts = {"bit.ly": [PUBLIC_IP], "www.coupang.com": [PUBLIC_IP]}
    probe.routes = {"https://bit.ly/x": (301, "https://www.coupang.com/")}
    data = analyze(client, "https://bit.ly/x").json()["data"]
    assert data["verdict"] == "SAFE"
    assert data["displayDomain"] == "www.coupang.com"
    assert data["redirectCount"] == 1


def test_shortener_without_destination_fails(client, probe):
    probe.hosts = {"bit.ly": [PUBLIC_IP]}
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
        ({"mixed.example.com": [PUBLIC_IP, "192.168.0.10"]}, "https://mixed.example.com/"),
    ],
)
def test_private_targets_are_blocked(client, probe, hosts, url):
    probe.hosts = hosts
    r = analyze(client, url)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "PRIVATE_NETWORK_TARGET"
    assert probe.fetched == []


def test_redirect_to_private_address_is_blocked(client, probe):
    probe.hosts = {"evil.com": [PUBLIC_IP]}
    probe.routes = {"https://evil.com/": (302, "http://169.254.169.254/")}
    r = analyze(client, "https://evil.com/")
    assert r.json()["error"]["code"] == "PRIVATE_NETWORK_TARGET"
    assert probe.fetched == ["https://evil.com/"]


@pytest.mark.parametrize(("redirects", "status"), [(5, 200), (6, 422)])
def test_redirect_limit(client, probe, redirects, status):
    probe.hosts = {"hop.com": [PUBLIC_IP]}
    probe.routes = {f"https://hop.com/{i}": (302, f"/{i + 1}") for i in range(redirects)}
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
def test_invalid_input(client, probe, url, status, code):
    r = analyze(client, url)
    assert r.status_code == status
    assert r.json()["success"] is False
    assert r.json()["error"]["code"] == code


def test_missing_url_is_invalid_request(client, probe):
    r = client.post("/api/v1/analyses", json={})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_REQUEST"


def test_timeout(client, probe):
    probe.hosts = {"slow.com": [PUBLIC_IP]}
    probe.delay = 1
    app.dependency_overrides[get_settings] = lambda: Settings(analysis_timeout_seconds=0.05)
    r = analyze(client, "https://slow.com/")
    assert r.status_code == 504
    assert r.json()["error"]["code"] == "ANALYSIS_TIMEOUT"


@pytest.mark.parametrize(
    ("error", "code"),
    [(httpx.ConnectError("refused"), "ANALYSIS_FAILED"), (RuntimeError("bug"), "ANALYSIS_FAILED")],
)
def test_failures_are_never_safe(client, probe, error, code):
    probe.hosts = {"down.com": [PUBLIC_IP]}
    probe.error = error
    r = analyze(client, "https://down.com/")
    assert r.status_code == 500
    assert r.json()["success"] is False
    assert r.json()["error"]["code"] == code


def test_client_request_id_returns_same_result(client, probe):
    probe.hosts = {"www.naver.com": [PUBLIC_IP]}
    first = analyze(client, "https://www.naver.com/", clientRequestId="scan-1").json()
    second = analyze(client, "https://www.naver.com/", clientRequestId="scan-1").json()
    assert first["data"]["analysisId"] == second["data"]["analysisId"]
    assert len(probe.fetched) == 1


def test_rate_limit(client, probe):
    probe.hosts = {"www.naver.com": [PUBLIC_IP]}
    app.dependency_overrides[get_settings] = lambda: Settings(analysis_rate_limit_per_minute=2)
    codes = [analyze(client, "https://www.naver.com/").status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_expired_sessions_are_purged(client, probe):
    probe.hosts = {"www.naver.com": [PUBLIC_IP]}
    app.dependency_overrides[get_settings] = lambda: Settings(analysis_ttl_minutes=-1)
    analyze(client, "https://www.naver.com/")
    analyze(client, "https://www.naver.com/")
    with SessionLocal() as db:
        expired = db.scalars(
            select(AnalysisSession).where(AnalysisSession.expires_at <= datetime.now(UTC))
        ).all()
    # 두 번째 저장 시 첫 번째(만료) 세션이 지워져 방금 저장한 것만 남는다
    assert len(expired) == 1
