# QR 피싱 탐지 API (Backend)

FastAPI 기반 URL 분석 서버. QR 해독은 클라이언트에서 하고, 서버는 추출된 URL만 받아 `SAFE` / `SUSPICIOUS` 로 판정한다.

## 실행

Python 3.12, PostgreSQL 16 기준. DB는 Docker Compose 로 띄우고 스키마는 Alembic으로 관리한다.
Docker DB는 이미 설치된 PostgreSQL과 겹치지 않도록 호스트 포트 **5433** 을 쓴다.

### Docker (권장)

저장소 루트에서 실행한다. PostgreSQL 과 백엔드를 함께 띄우고, 시작할 때 `alembic upgrade head` 를 적용하며, 소스 변경 시 자동으로 다시 로드한다.

```bash
docker compose up --build                     # http://localhost:8000/docs
docker compose exec backend pytest            # 테스트
docker compose exec backend alembic revision --autogenerate -m "설명"   # 마이그레이션 생성
```

### 백엔드만 venv 로 실행

DB 는 Docker 로 띄운다 (`docker compose up -d db`, `localhost:5433`).

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env

alembic upgrade head            # DB 스키마 생성·갱신 (모델 변경 후에도 실행)
fastapi dev app/main.py         # http://localhost:8000/docs
pytest                          # 테스트 (기본 SQLite, 마이그레이션으로 생성)
TEST_DATABASE_URL=postgresql+psycopg://qr:qr@localhost:5433/qr_test pytest   # PostgreSQL 로 테스트 (qr_test DB 를 지우고 다시 만든다)
ruff check . && ruff format .   # 린트/포맷
```

### 모델을 바꿨을 때

```bash
alembic revision --autogenerate -m "설명"   # migrations/versions 에 파일 생성 → 내용 확인
alembic upgrade head
```

모델과 마이그레이션이 어긋나면 `tests/test_setup.py::test_models_match_migrations` 가 실패한다.

### 휴대폰에서 테스트

카메라는 HTTPS에서만 동작하므로 프론트 개발 서버(5173)를 터널로 연다. `/api` 는 Vite가 백엔드로 프록시한다.

```bash
cloudflared tunnel --url http://localhost:5173   # 또는 ngrok http 5173
```

## 공통 규칙

- Base URL `/api/v1`
- 모든 응답은 `{ success, data | error, requestId }` 형식 (JSON 필드는 camelCase)
- `X-Request-ID` 헤더를 보내면 그대로 `requestId` 로 사용하고, 없으면 서버가 `req_<ULID>` 를 발급한다
- 오류 코드와 HTTP 상태는 `app/core/errors.py` 에 API 명세 5장 기준으로 정의되어 있다. 엔드포인트에서는 `raise AppError(ErrorCode.XXX)` 로 던지면 공통 오류 응답으로 변환된다

## 구조

```
backend/
├── alembic.ini
├── migrations/             # Alembic 마이그레이션 (versions/)
└── app/
    ├── main.py             # 앱 생성, 미들웨어, 라우터 등록, 세션 정리 작업 시작
    ├── api/
    │   ├── deps.py         # DbSession, AppSettings 의존성
    │   └── v1/
    │       ├── router.py   # v1 라우터 (엔드포인트 등록)
    │       └── endpoints/  # health
    ├── core/               # 설정, 오류 코드·핸들러, Request ID 미들웨어, ID 생성, 요청 제한(slowapi)
    ├── db/session.py       # SQLAlchemy 엔진/세션 (PostgreSQL, psycopg)
    ├── jobs/               # 24시간 지난 분석 세션 삭제 (앱 실행 중 1시간마다)
    ├── models/             # SQLAlchemy 모델 (analysis_sessions)
    └── schemas/            # 요청/응답 스키마 (CamelModel, ApiResponse[T])
```

## 요청 제한

`slowapi` 를 사용한다. 엔드포인트에 다음처럼 붙이고, 함수 인자로 `request: Request` 를 받아야 한다.
초과 시 공통 오류 형식의 `429 RATE_LIMIT_EXCEEDED` 로 응답한다.

```python
from app.core.rate_limit import limiter

@router.post("/analyses")
@limiter.limit(lambda: get_settings().analysis_rate_limit)
async def create_analysis(request: Request, ...): ...
```

IP는 `X-Forwarded-For` 의 첫 번째 값 기준이다 (Vite 프록시·터널이 붙여 준다).

## API (MVP)

| Method | Path | 설명 | 상태 |
| --- | --- | --- | --- |
| GET | `/health` | 서비스 상태 확인 | ✅ |
| POST | `/analyses` | URL 분석 | TODO |
| GET | `/analyses/{analysisId}` | 분석 결과 조회 | TODO |
| POST | `/intent-guidance` | 접속 의도 분석·공식 사이트 안내 | TODO |
