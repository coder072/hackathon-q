from datetime import UTC, datetime, timedelta

import pytest

from app.core.ids import new_id
from app.db.session import SessionLocal
from app.jobs.anonymize_sessions import anonymize_old_sessions, strip_query
from app.models.analysis_session import AnalysisSession
from app.schemas.analysis import AnalysisResult, RecommendedAction, Verdict

NOW = datetime.now(UTC)


def _store(age_hours: float) -> str:
    created = NOW - timedelta(hours=age_hours)
    result = AnalysisResult(
        analysis_id=new_id("ana"),
        verdict=Verdict.SUSPICIOUS,
        score=4,
        recommended_action=RecommendedAction.ASK_INTENT,
        original_url="https://bit.ly/abc?phone=01012345678#otp",
        final_url="https://naver-event.com/login?token=secret",
        display_domain="naver-event.com",
        redirect_count=1,
        checks=[],
        analyzed_at=created,
        expires_at=created + timedelta(minutes=20),
    )
    with SessionLocal() as db:
        db.add(
            AnalysisSession(
                id=result.analysis_id,
                score=result.score,
                verdict=result.verdict,
                recommended_action=result.recommended_action,
                client_request_id=f"scan-{result.analysis_id}",
                result_json=result.model_dump_json(by_alias=True),
                created_at=created,
                expires_at=result.expires_at,
            )
        )
        db.commit()
    return result.analysis_id


def _row(analysis_id: str) -> AnalysisSession:
    with SessionLocal() as db:
        return db.get(AnalysisSession, analysis_id)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://a.com/p?token=1#x", "https://a.com/p"),
        ("http://a.com:8080/?q=1", "http://a.com:8080/"),
        ("https://a.com/path", "https://a.com/path"),
    ],
)
def test_strip_query(url, expected):
    assert strip_query(url) == expected


def test_sessions_older_than_24_hours_are_anonymized_not_deleted(client):
    old, recent = _store(age_hours=25), _store(age_hours=1)

    anonymize_old_sessions(NOW)

    row = _row(old)
    assert row is not None  # 지우지 않고 영구 보관한다
    assert row.anonymized_at is not None
    assert row.client_request_id is None
    assert (row.score, row.verdict) == (4, "SUSPICIOUS")

    # 조회 API 로도 쿼리가 제거된 URL 이 나온다
    data = client.get(f"/api/v1/analyses/{old}").json()["data"]
    assert data["originalUrl"] == "https://bit.ly/abc"
    assert data["finalUrl"] == "https://naver-event.com/login"
    assert data["displayDomain"] == "naver-event.com"

    # 24시간이 지나지 않은 세션은 그대로다
    fresh = _row(recent)
    assert fresh.anonymized_at is None
    assert fresh.client_request_id == f"scan-{recent}"
    assert "phone=01012345678" in fresh.result_json


def test_anonymization_runs_once_per_session():
    old = _store(age_hours=30)
    anonymize_old_sessions(NOW)
    first = _row(old).anonymized_at

    anonymize_old_sessions(NOW + timedelta(hours=1))
    assert _row(old).anonymized_at == first
