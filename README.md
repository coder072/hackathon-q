# hackathon-q
AI와 맞짱뜨는 밤 Q팀 해커톤 래포입니다.

QR 코드 속 링크를 열기 전에 피싱 여부를 판정하는 PWA. 배포 없이 로컬에서 실행한다.

| 구성 | 기술 |
| --- | --- |
| 프론트엔드 (`frontend/`) | React, TypeScript, Vite, vite-plugin-pwa, qr-scanner (Node 22) |
| 백엔드 (`backend/`) | FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL 16 (Python 3.12) |
| URL 분석 | httpx, tldextract, idna, rapidfuzz |
| 의도 분류 | Claude API (4~6점 분석에서만 호출) |
| 요청 제한 / ID | slowapi / python-ulid |
| 테스트·CI | pytest, respx, Ruff, oxlint, GitHub Actions |
| 로컬 실행 | Docker Compose (PostgreSQL + 백엔드), Vite 개발 서버 (프론트) |

## 로컬 실행

```bash
# 터미널 1: PostgreSQL + 백엔드 (http://localhost:8000) — 마이그레이션 자동 적용
docker compose up --build

# 터미널 2: 프론트 (http://localhost:5173, /api 는 백엔드로 프록시)
cd frontend && npm install && npm run dev
```

Docker 없이 실행하는 방법과 휴대폰 테스트(Cloudflare Tunnel / ngrok)는 [backend/README.md](backend/README.md), [frontend/README.md](frontend/README.md) 참고.

## 개발 흐름

- **작업하는 동안 `docker compose up -d` 를 켜 둔다.** 백엔드는 코드를 저장하면 컨테이너 안에서 자동으로 다시 로드된다.
- `git pull` 후 `backend/requirements*.txt` 나 `Dockerfile` 이 바뀌었으면 `docker compose up -d --build` 로 다시 빌드한다. 마이그레이션은 백엔드가 시작할 때 자동 적용된다.
- 모델을 바꿨으면 마이그레이션을 만든다: `docker compose exec backend alembic revision --autogenerate -m "설명"`
- 테스트·린트: `docker compose exec backend pytest`, `docker compose exec backend ruff check .`
- 끝나면 `docker compose down` (DB 데이터는 유지, 완전히 지우려면 `docker compose down -v`)
