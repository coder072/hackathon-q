def test_health(client):
    r = client.get("/api/v1/health", headers={"X-Request-ID": "req_test"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["status"] == "UP"
    assert body["requestId"] == "req_test"


def test_analysis_suspicious(client, monkeypatch):
    r = client.post(
        "/api/v1/analyses",
        json={"url": "http://naver-login.example/verify", "source": "CAMERA"},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["verdict"] == "SUSPICIOUS"
    assert data["score"] == 5
    assert data["displayDomain"] == "naver-login.example"
    assert data["analysisId"].startswith("ana_")
    detected = {c["code"] for c in data["checks"] if c["detected"]}
    assert detected == {"HTTPS_NOT_USED", "LOOKALIKE_DOMAIN"}


def test_analysis_safe(client):
    r = client.post("/api/v1/analyses", json={"url": "https://www.naver.com", "source": "IMAGE"})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["verdict"] == "SAFE"


def test_analysis_rejects_private_ip(client):
    r = client.post("/api/v1/analyses", json={"url": "http://169.254.169.254/", "source": "CAMERA"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "PRIVATE_NETWORK_TARGET"


def test_analysis_unsupported_scheme(client):
    r = client.post("/api/v1/analyses", json={"url": "ftp://example.com", "source": "CAMERA"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "UNSUPPORTED_SCHEME"


def test_analysis_dedup_by_client_request_id(client):
    body = {"url": "https://example.com", "source": "CAMERA", "clientRequestId": "scan_1"}
    a = client.post("/api/v1/analyses", json=body).json()["data"]["analysisId"]
    b = client.post("/api/v1/analyses", json=body).json()["data"]["analysisId"]
    assert a == b


def test_get_analysis(client):
    a = client.post("/api/v1/analyses", json={"url": "https://example.com", "source": "CAMERA"})
    aid = a.json()["data"]["analysisId"]
    assert client.get(f"/api/v1/analyses/{aid}").status_code == 200
    r = client.get("/api/v1/analyses/ana_missing")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "ANALYSIS_NOT_FOUND"


def test_report_flow(client):
    a = client.post("/api/v1/analyses", json={"url": "http://nav3r.com", "source": "CAMERA"})
    aid = a.json()["data"]["analysisId"]

    r = client.post("/api/v1/reports", json={"analysisId": aid, "reason": "IMPERSONATION"})
    assert r.status_code == 201, r.text
    assert r.json()["data"]["status"] == "PENDING"
    assert r.json()["data"]["reportId"].startswith("rpt_")

    dup = client.post("/api/v1/reports", json={"analysisId": aid, "reason": "OTHER"})
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "REPORT_ALREADY_EXISTS"

    bad = client.post("/api/v1/reports", json={"analysisId": aid, "reason": "NOPE"})
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "INVALID_REPORT_REASON"

    missing = client.post("/api/v1/reports", json={"analysisId": "ana_x", "reason": "OTHER"})
    assert missing.status_code == 404
