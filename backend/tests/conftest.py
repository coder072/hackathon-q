import os

os.environ["DATABASE_URL"] = "sqlite:///./data/test.db"

from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.analyzer import pipeline  # noqa: E402
from app.analyzer.redirects import RedirectTrace  # noqa: E402
from app.db.session import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """외부 요청 없이 리디렉션 없는 것으로 간주한다."""

    async def fake_trace(start, **_):
        return RedirectTrace(final=start, chain=[start.url])

    monkeypatch.setattr(pipeline, "trace_redirects", fake_trace)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def pytest_sessionfinish(session, exitstatus):
    Path("data/test.db").unlink(missing_ok=True)
