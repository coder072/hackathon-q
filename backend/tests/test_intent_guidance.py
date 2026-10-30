from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.db.session import SessionLocal
from app.models.analysis_session import AnalysisSession


def create_analysis(*, score: int = 5, action: str = "ASK_INTENT", expired: bool = False) -> str:
    analysis_id = f"ana_{uuid4().hex}"
    expires_at = datetime.now(UTC) + timedelta(minutes=-1 if expired else 20)
    with SessionLocal() as db:
        db.add(
            AnalysisSession(
                id=analysis_id,
                score=score,
                recommended_action=action,
                expires_at=expires_at,
            )
        )
        db.commit()
    return analysis_id


def test_intent_guidance_structures_service_action_and_keywords(client):
    analysis_id = create_analysis()

    response = client.post(
        "/api/v1/intent-guidance",
        headers={"X-Request-ID": "req_intent"},
        json={"analysisId": analysis_id, "userMessage": "네이버 로그인해서 메일 확인하려고"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["requestId"] == "req_intent"
    assert body["data"]["analysisId"] == analysis_id
    assert body["data"]["serviceKey"] == "naver"
    assert body["data"]["serviceName"] == "네이버"
    assert body["data"]["intentCode"] == "SERVICE_LOGIN"
    assert body["data"]["confidence"] >= 0.9
    assert "메일" in body["data"]["additionalKeywords"]
    assert body["data"]["guidanceStatus"] == "NOT_FOUND"
    assert body["data"]["suggestions"] == []
    assert response.headers["Cache-Control"] == "no-store"


def test_intent_guidance_requests_missing_service(client):
    analysis_id = create_analysis()

    response = client.post(
        "/api/v1/intent-guidance",
        json={"analysisId": analysis_id, "userMessage": "택배 배송 조회하려고"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["guidanceStatus"] == "NEEDS_CLARIFICATION"
    assert data["intentCode"] == "DELIVERY_TRACKING"
    assert data["serviceName"] is None
    assert "서비스 이름" in data["followUpQuestion"]


def test_intent_guidance_rejects_invalid_message(client):
    analysis_id = create_analysis()

    response = client.post(
        "/api/v1/intent-guidance",
        json={"analysisId": analysis_id, "userMessage": "   "},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_INTENT_MESSAGE"


def test_intent_guidance_rejects_sensitive_data(client):
    analysis_id = create_analysis()

    response = client.post(
        "/api/v1/intent-guidance",
        json={"analysisId": analysis_id, "userMessage": "네이버 인증번호 123456"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "SENSITIVE_DATA_DETECTED"


def test_intent_guidance_requires_active_analysis(client):
    response = client.post(
        "/api/v1/intent-guidance",
        json={"analysisId": "ana_missing", "userMessage": "네이버 로그인"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ANALYSIS_NOT_FOUND"


def test_intent_guidance_rejects_non_ambiguous_analysis(client):
    analysis_id = create_analysis(score=8, action="BLOCK")

    response = client.post(
        "/api/v1/intent-guidance",
        json={"analysisId": analysis_id, "userMessage": "네이버 로그인"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INTENT_GUIDANCE_NOT_ALLOWED"


def test_intent_guidance_rejects_expired_analysis(client):
    analysis_id = create_analysis(expired=True)

    response = client.post(
        "/api/v1/intent-guidance",
        json={"analysisId": analysis_id, "userMessage": "네이버 로그인"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ANALYSIS_NOT_FOUND"
