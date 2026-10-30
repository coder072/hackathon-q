import os

# 기본은 SQLite 로 빠르게 실행한다. PostgreSQL 로 돌리려면 TEST_DATABASE_URL 을 지정한다.
# (주의: 지정한 DB 의 테이블을 모두 지우고 다시 만든다)
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "sqlite:///./data/test.db")

from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"
TEST_DB = Path("data/test.db")


@pytest.fixture(scope="session", autouse=True)
def database():
    # 테스트 DB 도 실제와 같은 Alembic 마이그레이션으로 만든다
    TEST_DB.unlink(missing_ok=True)
    config = Config(str(ALEMBIC_INI))
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield
    TEST_DB.unlink(missing_ok=True)


@pytest.fixture
def alembic_config() -> Config:
    return Config(str(ALEMBIC_INI))


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
