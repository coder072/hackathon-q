from alembic import command
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter

from app.core.handlers import register_exception_handlers
from app.core.middleware import RequestIdMiddleware
from app.core.rate_limit import client_ip


def test_models_match_migrations(alembic_config):
    # 모델을 바꾸고 마이그레이션을 추가하지 않으면 실패한다
    command.check(alembic_config)


def _rate_limited_app() -> FastAPI:
    app = FastAPI()
    app.state.limiter = Limiter(key_func=client_ip)
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)

    @app.get("/limited")
    @app.state.limiter.limit("2/minute")
    def limited(request: Request) -> dict:
        return {"ip": client_ip(request)}

    return app


def test_rate_limit_uses_forwarded_ip_and_error_envelope():
    client = TestClient(_rate_limited_app())
    alice = {"X-Forwarded-For": "1.1.1.1, 76.76.21.21"}

    assert client.get("/limited", headers=alice).json() == {"ip": "1.1.1.1"}
    assert client.get("/limited", headers=alice).status_code == 200
    r = client.get("/limited", headers=alice)
    assert r.status_code == 429
    assert r.json()["success"] is False
    assert r.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert r.json()["requestId"]

    # 다른 사용자는 영향을 받지 않는다
    assert client.get("/limited", headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 200
