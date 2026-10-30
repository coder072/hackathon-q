def test_health(client):
    r = client.get("/api/v1/health", headers={"X-Request-ID": "req_test"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["status"] == "UP"
    assert body["requestId"] == "req_test"
    assert r.headers["X-Request-ID"] == "req_test"


def test_unknown_route_uses_error_envelope(client):
    r = client.get("/api/v1/nope")
    assert r.status_code == 404
    body = r.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["requestId"]
