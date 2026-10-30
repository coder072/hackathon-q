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
```

`qr_test` DB 는 DB 볼륨을 처음 만들 때 자동으로 생긴다. 기존 볼륨에 없으면 `docker compose exec db createdb -U qr qr_test` 로 만든다.

```bash
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
    │       └── endpoints/  # health, analyses, intent_guidance
    ├── core/               # 설정, 오류 코드·핸들러, Request ID 미들웨어, ID 생성, 요청 제한(slowapi)
    ├── db/session.py       # SQLAlchemy 엔진/세션 (PostgreSQL, psycopg)
    ├── catalog/            # 차단·허용 목록, 유명 서비스 도메인, 단축 URL 목록 (JSON)
    ├── jobs/               # 24시간 지난 분석 세션 URL 익명화 (앱 실행 중 1시간마다)
    ├── models/             # SQLAlchemy 모델 (analysis_sessions)
    ├── schemas/            # 요청/응답 스키마 (CamelModel, ApiResponse[T])
    └── services/
        ├── analyses/       # POST /analyses
        │   ├── parsing.py  # URL 정규화, IDNA (URL-001)
        │   ├── analyzer.py # DNS·SSRF 검사, 리디렉션 추적, 분석 흐름 (URL-003·004·009)
        │   ├── rules.py    # 위험 점수 규칙, 차단·허용 목록 (URL-002·005~008)
        │   └── sessions.py # 분석 세션 저장·조회
        └── intent/         # POST /intent-guidance
            ├── assessment.py # QR 링크·의도 비교 판단 검증, 규칙 판단
            ├── catalog.py  # 공식 사이트 카탈로그 (catalog/official_sites.json)
            ├── sensitive.py # 민감정보 패턴 (INT-005)
            ├── rules.py    # 규칙 기반 분류기 (LLM 대체)
            ├── llm.py      # OpenAI 의도 분류기 (Structured Outputs, 카탈로그 키만)
            └── guidance.py # 분류 → 공식 사이트 후보 조립
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

## URL 분석 (`POST /analyses`)

`정규화 → 차단 목록 → DNS 확인·SSRF 검사 → 검증한 IP로 접속 → 리디렉션이면 반복 → 점수 합산` 순서로 처리한다.

- 리디렉션은 자동으로 따라가지 않고 `httpx` 로 한 단계씩 직접 요청한다. 매 단계마다 DNS 결과의 모든 IP가 공인 주소인지 확인하고, 검증한 IP로 직접 접속한다 (Host 헤더·TLS SNI 는 원래 도메인이라 인증서 검사는 그대로 동작한다).
- 최대 5회 리디렉션, 전체 5초 제한. 응답 본문은 읽지 않는다.
- 대상 서버에 접속하지 못하면(응답 없음·연결 거부) 그때까지 확인한 주소로 점수를 매긴다. **4점 이상이면 피싱 의심으로 판정**하고, 4점 미만이면 안전으로 판정하지 않고 `ANALYSIS_TIMEOUT`/`ANALYSIS_FAILED` 로 응답한다.
- 차단 목록에 걸리면 그 주소에는 접속하지 않고 즉시 10점 처리한다.
- 등록 도메인은 `tldextract`(내장 공개 접미사 목록, 네트워크 조회 없음), 국제화 도메인은 `idna`(IDNA 2008), 유사 도메인은 `rapidfuzz` 편집 거리로 판단한다.
- 분석 결과는 `analysis_sessions` 에 저장된다. `expiresAt`(20분)은 `POST /intent-guidance` 같은 후속 행동의 유효 시간이고, `GET /analyses/{analysisId}` 조회는 기간 제한이 없다.
- 분석 결과는 지우지 않고 영구 보관한다. 24시간이 지나면 URL 의 쿼리·프래그먼트와 `clientRequestId` 를 지운다 (`app/jobs/anonymize_sessions.py`, NFR-007). 도메인·경로·점수·판정·검사 결과는 남는다.
- 차단·허용 목록은 관리자 API 없이 `app/catalog/*.json` 을 수정한다.
- 테스트는 `respx` 로 HTTP 를 가로채고 DNS 는 가짜 Resolver 로 바꿔 네트워크 없이 실행한다.

## 접속 의도 안내 (`POST /intent-guidance`)

`세션 검사(4~6점·20분 이내) → 메시지 검증·민감정보 차단 → AI 판단(의도 분류 + QR 링크 비교) → 서버 검증 → 공식 사이트 카탈로그 조회` 순서로 처리한다.

- AI 에는 사용자 문장과 분석 요약(최종 도메인·점수·리디렉션·탐지 근거)만 넘긴다. URL 전체(경로·쿼리)는 넘기지 않는다.
- AI 는 `matchesIntent`(QR 링크가 원한 서비스의 공식 도메인인지)와 사용자용 설명 `explanation` 을 판단한다. 응답의 `assessment` 에 담긴다.
- 서버 검증: 공식 도메인이 아닌데 '일치'라고 하면 규칙 판단으로 대체하고, 설명의 URL·허용되지 않은 도메인은 가린다. **원래 링크를 열어도 된다는 결론은 없다**(4~6점은 항상 차단).

- 의도 분류는 `backend/.env` 에 `OPENAI_API_KEY`(팩트챗 키)가 있으면 팩트챗 게이트웨이(OpenAI 호환, `INTENT_MODEL` 기본 OpenAI `gpt-5.4`)로, 없거나 실패(크레딧 부족 등)·5초 초과 시 규칙 기반으로 한다. `.env` 는 `cp .env.example .env` 로 만들고 키를 넣은 뒤 `docker compose up -d` 로 컨테이너를 다시 만든다 (`restart` 는 `.env` 를 다시 읽지 않는다). OpenAI 키를 직접 쓰려면 `OPENAI_BASE_URL=` 을 비우고 OpenAI 모델 이름을 `INTENT_MODEL` 에 넣는다.
- LLM 은 카탈로그의 `serviceKey`·`intentCode` 중에서만 고른다(구조화 출력). URL 은 `app/catalog/official_sites.json` 에서만 나오고, 모든 URL 이 허용 목록 도메인인지 테스트로 확인한다.
- 의도를 알 수 없거나 후보가 없어도 오류가 아닌 `200` + `NEEDS_CLARIFICATION`/`NOT_FOUND` 로 응답한다(원래 링크 차단 유지).
- 민감정보(비밀번호·인증번호·계좌·주민번호·카드번호)는 LLM 에 보내기 전에 `422 SENSITIVE_DATA_DETECTED`. 사용자 원문은 저장·로그하지 않는다.
- 테스트는 가짜 분류기·가짜 클라이언트로 실행한다(실제 API 호출 없음). openai SDK 는 `httpx2` 를 써서 `respx` 로는 가로챌 수 없다.

## API (MVP)

| Method | Path | 설명 | 상태 |
| --- | --- | --- | --- |
| GET | `/health` | 서비스 상태 확인 | ✅ |
| POST | `/analyses` | URL 분석 | ✅ |
| GET | `/analyses/{analysisId}` | 분석 결과 조회 (저장된 결과, 기간 제한 없음) | ✅ |
| POST | `/intent-guidance` | 접속 의도 분석·공식 사이트 안내 (4~6점) | ✅ |
