# QR 피싱 탐지 PWA (Frontend)

Vite + React 19 + TypeScript + Tailwind CSS v4 + vite-plugin-pwa.
카메라로 QR을 해독하고, 추출한 URL만 백엔드(`/api/v1`)로 보내 `SAFE` / `SUSPICIOUS` 판정을 받는다.

## 실행

```bash
cd frontend
npm install
cp .env.example .env.local   # 필요 시

npm run dev       # http://localhost:5173  (/api → http://localhost:8000 프록시)
npm run build     # 타입 체크 + 프로덕션 빌드 (서비스 워커 생성)
npm run preview   # 빌드 결과 확인 (PWA 설치·캐시 테스트는 여기서)
npm run lint
```

> 카메라와 서비스 워커는 HTTPS 또는 `localhost` 에서만 동작한다. 휴대폰 실기기 테스트는 배포 URL이나 HTTPS 터널(ngrok, cloudflared 등)을 사용한다.

## 화면 / 라우트

| 화면 ID | 경로 | 설명 |
| --- | --- | --- |
| SCR-001 | `/` | 카메라 스캔 (후면 카메라 우선, 비 URL QR 은 분석하지 않음) |
| SCR-002 | `/analyzing` | `POST /analyses` 호출, 취소 |
| SCR-003/004 | `/result` | 안전(링크 열기 버튼) / 피싱 의심(돌아가기, 판정 근거, 신고) |
| SCR-005 | `/intent` | 4~6점일 때만 진입, 접속 의도 자연어 입력 |
| SCR-006 | `/suggestions` | `POST /intent-guidance` 결과의 검증된 공식 사이트 (최대 3개) |
| SCR-007 | (각 화면 내) | 카메라 거부, 네트워크·분석·의도 분석 오류 |
| SCR-008 | `/install` | 홈 화면 설치 안내 |
| SCR-009 | `/admin` | 관리자 (Phase 3, 준비 중) |

## 구조

```
src/
├── api/            # fetch 클라이언트, 명세 기반 타입, 엔드포인트 함수
├── components/     # Layout(오프라인 배너), 공통 UI, 신고 폼
├── hooks/          # useQrScanner(qr-scanner), useOnlineStatus
├── lib/            # 판정 구간(SAFE / 4~6 / 7~10), 오류 코드별 안내 문구
├── pages/          # 화면
└── state/          # 스캔 흐름 공유 상태 (Context)
```

## 안전 원칙 (구현 시 지켜야 할 것)

- 스캔만으로 외부 링크를 열지 않는다. 링크는 사용자가 버튼을 눌렀을 때만 연다.
- 피싱 의심 결과에는 원래 링크를 여는 버튼을 두지 않는다.
- 네트워크 오류·분석 실패는 절대 안전으로 표시하지 않는다.
- 공식 사이트 추천은 서버가 반환한 `verified` 후보만 표시한다.
- `/api` 응답은 서비스 워커가 캐시하지 않는다.
