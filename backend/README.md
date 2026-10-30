# QR 피싱 탐지 API (Backend)

FastAPI 기반 URL 분석 서버. QR 해독은 클라이언트에서 하고, 서버는 추출된 URL만 받아 `SAFE` / `SUSPICIOUS` 로 판정한다.

## 실행

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env

fastapi dev app/main.py        # http://localhost:8000/docs
pytest                          # 테스트
ruff check . && ruff format .   # 린트/포맷
```

## 공통 규칙

- Base URL `/api/v1`
- 모든 응답은 `{ success, data | error, requestId }` 형식 (JSON 필드는 camelCase)
- `X-Request-ID` 헤더를 보내면 그대로 `requestId` 로 사용하고, 없으면 서버가 `req_<ULID>` 를 발급한다
- 오류 코드와 HTTP 상태는 `app/core/errors.py` 에 API 명세 5장 기준으로 정의되어 있다. 엔드포인트에서는 `raise AppError(ErrorCode.XXX)` 로 던지면 공통 오류 응답으로 변환된다

## 구조

```
app/
├── main.py                 # 앱 생성, 미들웨어, 라우터 등록
├── api/
│   ├── deps.py             # DbSession, AppSettings 의존성
│   └── v1/
│       ├── router.py       # v1 라우터 (엔드포인트 등록)
│       └── endpoints/      # health
├── core/                   # 설정, 오류 코드·핸들러, Request ID 미들웨어, ID 생성
├── db/session.py           # SQLAlchemy 엔진/세션 (기본 SQLite, 시작 시 create_all)
├── models/                 # SQLAlchemy 모델
└── schemas/                # 요청/응답 스키마 (CamelModel, ApiResponse[T])
```

## API (MVP)

| Method | Path | 설명 | 상태 |
| --- | --- | --- | --- |
| GET | `/health` | 서비스 상태 확인 | ✅ |
| POST | `/analyses` | URL 분석 | TODO |
| GET | `/analyses/{analysisId}` | 분석 결과 조회 | TODO |
| POST | `/reports` | 피싱 의심 URL 신고 | TODO |
