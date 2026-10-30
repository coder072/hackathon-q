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

## API (Base URL `/api/v1`)

| Method | Path | 설명 | MVP |
| --- | --- | --- | --- |
| GET | `/health` | 서비스 상태 확인 | ✅ |
| POST | `/analyses` | URL 분석 | ✅ |
| GET | `/analyses/{analysisId}` | 분석 결과 조회 (24시간 보관) | ✅ |
| POST | `/reports` | 피싱 의심 URL 신고 | ✅ |
| * | `/admin/*` | 신고 검토, 차단·허용 목록 | TODO |

모든 응답은 `{ success, data | error, requestId }` 형식이며, `X-Request-ID` 헤더를 보내면 그대로 `requestId` 로 사용한다.

## 구조

```
app/
├── main.py                 # 앱 생성, 미들웨어, 라우터 등록
├── api/v1/endpoints/       # health, analyses, reports
├── core/                   # 설정, 오류 코드·핸들러, Request ID 미들웨어
├── db/session.py           # SQLAlchemy 엔진/세션 (기본 SQLite, 시작 시 create_all)
├── models/                 # Analysis, Report, BlocklistEntry, AllowlistEntry
├── schemas/                # 요청/응답 (JSON 은 camelCase)
├── services/               # 분석·신고 비즈니스 로직
└── analyzer/               # URL 분석 파이프라인
    ├── normalizer.py       # URL-001 정규화·검증
    ├── ssrf.py             # URL-009 사설 IP·메타데이터 주소 차단
    ├── redirects.py        # URL-003 리디렉션 추적 (홉마다 DNS 재검증, 최대 5회)
    ├── lookalike.py        # URL-005 유사 도메인
    ├── checks.py           # 검사 항목별 점수
    ├── scoring.py          # 0~3 SAFE / 4~10 SUSPICIOUS, 차단 목록 일치 시 10점
    └── pipeline.py         # 전체 흐름 (전체 5초 제한)
```

## 위험 점수

| 코드 | 조건 | 점수 |
| --- | --- | --- |
| `HTTPS_NOT_USED` | 최종 URL 이 HTTP | +1 |
| `LOOKALIKE_DOMAIN` | 유명 서비스 유사 도메인 | +4 |
| `SUSPICIOUS_URL_STRUCTURE` | 긴 URL·다수 하위 도메인·특수문자 | +1 |
| `DIRECT_IP_ACCESS` | IP 주소 직접 사용 | +3 |
| `BLOCKLIST_MATCH` | 차단 목록 일치 | 10 확정 |
| `EXCESSIVE_REDIRECTS` | 리디렉션 2회 초과 | +1 |
| `ALLOWLIST_MATCH` | 허용 목록 일치 (근거 기록용) | 0 |

분석 실패(DNS 실패, 타임아웃, 연결 불가 등)는 `SAFE` 가 아니라 오류 응답으로 반환한다.

## TODO

- [ ] 관리자 API + 인증
- [ ] 요청 횟수 제한 (분석 분당 30회, 신고 분당 5회)
- [ ] DNS 리바인딩 방지를 위한 IP pinning transport
- [ ] 보관 기간 지난 분석 결과 정리 작업
- [ ] 차단 목록 초기 데이터
