from datetime import UTC, datetime, timedelta

import pytest

from app.api.v1.endpoints import intent_guidance
from app.core.config import get_settings
from app.core.ids import new_id
from app.core.rate_limit import limiter
from app.db.session import SessionLocal
from app.main import app
from app.models.analysis_session import AnalysisSession
from app.schemas.analysis import AnalysisResult, CheckCode, CheckResult
from app.services.analyses.rules import load_catalog, matches_domain
from app.services.intent.catalog import load_official_sites
from app.services.intent.rules import Classification


class FakeLlm:
    def __init__(self, result: Classification | None = None):
        self.result = result
        self.calls: list[str] = []
        self.contexts: list = []

    async def classify(self, message: str, context=None) -> Classification | None:
        self.calls.append(message)
        self.contexts.append(context)
        return self.result


@pytest.fixture
def llm():
    fake = FakeLlm()
    app.dependency_overrides[intent_guidance.get_intent_classifier] = lambda: fake
    limiter.reset()
    yield fake
    app.dependency_overrides.clear()


def session(
    score=5, action="ASK_INTENT", expires_in=timedelta(minutes=20), domain="naver.github.io"
) -> str:
    analysis_id = new_id("ana")
    now = datetime.now(UTC)
    result = AnalysisResult(
        analysis_id=analysis_id,
        verdict="SAFE" if score <= 3 else "SUSPICIOUS",
        score=score,
        recommended_action=action,
        original_url=f"https://{domain}/",
        final_url=f"https://{domain}/",
        display_domain=domain,
        redirect_count=0,
        checks=[
            CheckResult(
                code=CheckCode.LOOKALIKE_DOMAIN,
                detected=True,
                score=4,
                message="유명 서비스(naver)와 유사한 도메인입니다.",
            )
        ],
        analyzed_at=now,
        expires_at=now + expires_in,
    )
    with SessionLocal() as db:
        db.add(
            AnalysisSession(
                id=analysis_id,
                score=score,
                verdict="SAFE" if score <= 3 else "SUSPICIOUS",
                recommended_action=action,
                result_json=result.model_dump_json(by_alias=True),
                created_at=now,
                expires_at=now + expires_in,
            )
        )
        db.commit()
    return analysis_id


def guide(client, analysis_id, message):
    return client.post(
        "/api/v1/intent-guidance", json={"analysisId": analysis_id, "userMessage": message}
    )


def test_llm_match_returns_catalog_sites(client, llm):
    llm.result = Classification("korea_post", "DELIVERY_TRACKING", 0.93, "llm")
    r = guide(client, session(), "택배 왔다고 해서 찍었어요")

    assert r.status_code == 200
    assert r.headers["Cache-Control"] == "no-store"
    data = r.json()["data"]
    assert data["guidanceStatus"] == "MATCHED"
    assert (data["serviceKey"], data["serviceName"]) == ("korea_post", "우체국")
    assert data["intentCode"] == "DELIVERY_TRACKING"
    assert data["confidence"] == 0.93
    assert data["followUpQuestion"] is None
    urls = [s["url"] for s in data["suggestions"]]
    assert urls == [
        "https://service.epost.go.kr/iservice/usr/trace/usrtrc001k01.jsp",
        "https://www.epost.go.kr/",
    ]
    assert all(s["verified"] is True for s in data["suggestions"])
    assert llm.calls == ["택배 왔다고 해서 찍었어요"]


def test_rules_are_used_without_llm(client):
    app.dependency_overrides[intent_guidance.get_intent_classifier] = lambda: None
    limiter.reset()
    try:
        data = guide(client, session(), "네이버 로그인하려고").json()["data"]
    finally:
        app.dependency_overrides.clear()
    assert data["guidanceStatus"] == "MATCHED"
    assert data["suggestions"][0]["url"] == "https://nid.naver.com/nidlogin.login"
    assert data["confidence"] == 0.9


def test_llm_failure_falls_back_to_rules(client, llm):
    llm.result = None
    data = guide(client, session(), "카카오 로그인").json()["data"]
    assert (data["serviceKey"], data["intentCode"]) == ("kakao", "SERVICE_LOGIN")
    assert len(llm.calls) == 1


@pytest.mark.parametrize(
    ("result", "message", "question_part"),
    [
        (Classification("naver", None, 0.5, "llm"), "네이버", "네이버에서"),
        (Classification(None, "SERVICE_LOGIN", 0.5, "llm"), "로그인", "로그인을 하려고"),
        (Classification(None, "DELIVERY_TRACKING", 0.5, "llm"), "택배", "배송 조회를 하려고"),
        (Classification(None, None, 0.0, "llm"), "그냥 찍어봤어요", "예: 우체국"),
    ],
)
def test_incomplete_intent_asks_follow_up(client, llm, result, message, question_part):
    llm.result = result
    r = guide(client, session(), message)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["guidanceStatus"] == "NEEDS_CLARIFICATION"
    assert question_part in data["followUpQuestion"]
    assert data["suggestions"] == []


@pytest.mark.parametrize(
    ("make_id", "status", "code"),
    [
        (lambda: "ana_01M678S2BPFJKCZJV985R4Y90B", 404, "ANALYSIS_NOT_FOUND"),
        (lambda: "nope", 404, "ANALYSIS_NOT_FOUND"),
        (lambda: session(expires_in=timedelta(minutes=-1)), 404, "ANALYSIS_NOT_FOUND"),
        (lambda: session(score=1, action="OPEN_ALLOWED"), 409, "INTENT_GUIDANCE_NOT_ALLOWED"),
        (lambda: session(score=9, action="BLOCK"), 409, "INTENT_GUIDANCE_NOT_ALLOWED"),
    ],
)
def test_only_unexpired_ask_intent_sessions(client, llm, make_id, status, code):
    r = guide(client, make_id(), "네이버 로그인")
    assert r.status_code == status
    assert r.json()["error"]["code"] == code
    assert llm.calls == []


@pytest.mark.parametrize("message", ["", "   ", "가" * 301])
def test_invalid_message(client, llm, message):
    r = guide(client, session(), message)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_INTENT_MESSAGE"


@pytest.mark.parametrize(
    "message",
    [
        "네이버 비밀번호는 abcd1234 인데 로그인이 안돼요",
        "인증번호 123456 받았어요",
        "주민번호 900101-1234567",
        "카드 1234-5678-9012-3456 결제",
        "계좌번호 110-123-456789 로 송금",
    ],
)
def test_sensitive_data_is_rejected_before_llm(client, llm, message):
    r = guide(client, session(), message)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "SENSITIVE_DATA_DETECTED"
    assert llm.calls == []


def test_rate_limit(client, llm, monkeypatch):
    monkeypatch.setattr(get_settings(), "intent_rate_limit", "2/minute")
    analysis_id = session()
    codes = [guide(client, analysis_id, "네이버 로그인").status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_catalog_urls_are_verified_official_domains():
    # INT-004: 추천 URL 은 모두 HTTPS 이고 허용 목록(공식 도메인)에 속해야 한다
    allowlist = load_catalog().allowlist
    catalog = load_official_sites()
    intent_codes = {i.code for i in catalog.intents} | {"*"}
    for service in catalog.services:
        assert any("*" in site.intent_codes for site in service.sites), service.key
        for site in service.sites:
            assert site.url.startswith("https://"), site.url
            assert matches_domain(site.domain, allowlist), site.url
            assert set(site.intent_codes) <= intent_codes, site.name


def test_llm_judges_link_against_intent(client, llm):
    llm.result = Classification(
        "naver",
        "SERVICE_LOGIN",
        0.95,
        "llm",
        matches_intent=False,
        explanation="네이버 로그인을 원하셨지만 naver.github.io 는 네이버가 아니에요.",
    )
    data = guide(client, session(), "네이버 로그인").json()["data"]

    assert data["assessment"] == {
        "matchesIntent": False,
        "explanation": "네이버 로그인을 원하셨지만 naver.github.io 는 네이버가 아니에요.",
        "source": "llm",
    }
    # AI 에는 URL 전체가 아니라 도메인·점수·근거만 넘긴다
    context = llm.contexts[0]
    assert (context.domain, context.score) == ("naver.github.io", 5)
    assert context.findings == ("유명 서비스(naver)와 유사한 도메인입니다.",)


def test_llm_cannot_claim_match_for_non_official_domain(client, llm):
    llm.result = Classification(
        "naver",
        "SERVICE_LOGIN",
        1.0,
        "llm",
        matches_intent=True,
        explanation="안전해요. 열어도 돼요.",
    )
    data = guide(client, session(), "네이버 로그인").json()["data"]
    assert data["assessment"]["source"] == "rules"
    assert data["assessment"]["matchesIntent"] is False
    assert "공식 주소가 아닌 naver.github.io" in data["assessment"]["explanation"]


def test_explanation_never_contains_other_addresses(client, llm):
    llm.result = Classification(
        "naver",
        "SERVICE_LOGIN",
        0.9,
        "llm",
        matches_intent=False,
        explanation="https://evil.example/login이나 evil.example 대신 nid.naver.com을 쓰세요. "
        "naver.github.io로 연결되는 가짜예요.",
    )
    text = guide(client, session(), "네이버 로그인").json()["data"]["assessment"]["explanation"]
    assert "evil" not in text
    assert "nid.naver.com을" in text and "naver.github.io로" in text


@pytest.mark.parametrize(
    ("domain", "message", "matches", "phrase"),
    [
        ("naver.github.io", "네이버 로그인", False, "네이버를 이용하려 하셨지만"),
        ("nid.naver.com", "네이버 로그인", True, "네이버 공식 도메인(nid.naver.com)"),
        ("naver.github.io", "그냥 찍어봤어요", None, "naver.github.io 주소로 연결되고"),
    ],
)
def test_rule_assessment_without_llm(client, domain, message, matches, phrase):
    app.dependency_overrides[intent_guidance.get_intent_classifier] = lambda: None
    limiter.reset()
    try:
        data = guide(client, session(domain=domain), message).json()["data"]
    finally:
        app.dependency_overrides.clear()
    assert data["assessment"]["source"] == "rules"
    assert data["assessment"]["matchesIntent"] is matches
    assert phrase in data["assessment"]["explanation"]
