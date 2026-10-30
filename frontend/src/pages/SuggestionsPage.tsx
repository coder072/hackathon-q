import { Navigate, useNavigate } from 'react-router'
import { Button, ErrorView } from '../components/ui'
import { useScanFlow } from '../state/useScanFlow'

// SCR-006 공식 사이트 추천 화면 (RST-008, RST-009)
export function SuggestionsPage() {
  const navigate = useNavigate()
  const { guidance, reset } = useScanFlow()

  if (!guidance) return <Navigate to="/" replace />

  const goHome = () => {
    reset()
    navigate('/', { replace: true })
  }

  // 서버가 검증한 후보만 표시 (방어적으로 verified 재확인)
  const suggestions = guidance.suggestions.filter((s) => s.verified).slice(0, 3)

  if (guidance.guidanceStatus === 'NEEDS_CLARIFICATION') {
    return (
      <ErrorView
        title="목적을 조금 더 알려 주세요"
        message={guidance.followUpQuestion ?? '어떤 서비스에서 무엇을 하려는지 함께 입력해 주세요.'}
      >
        <Button onClick={() => navigate('/intent', { replace: true })}>다시 입력</Button>
        <Button variant="secondary" onClick={goHome}>
          다시 스캔
        </Button>
      </ErrorView>
    )
  }

  if (suggestions.length === 0) {
    return (
      <ErrorView
        title="원래 링크는 계속 차단돼요"
        message="확인된 공식 사이트를 찾지 못했어요. QR을 제공한 곳에 직접 확인해 주세요."
      >
        <Button onClick={goHome}>다시 스캔</Button>
      </ErrorView>
    )
  }

  return (
    <div className="flex flex-1 flex-col gap-4 py-6">
      <div>
        <p className="text-sm text-slate-400">이렇게 이해했어요</p>
        <h1 className="text-xl font-bold">
          {guidance.serviceName ?? '서비스 미확인'} · {guidance.intentCode ?? '의도 미확인'}
        </h1>
      </div>

      <ul className="space-y-3">
        {suggestions.map((s) => (
          <li key={s.url} className="rounded-xl bg-slate-900 p-4">
            <div className="flex items-center gap-2">
              <span className="font-semibold">{s.name}</span>
              <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-300">✔ 검증된 공식 사이트</span>
            </div>
            <p className="mt-1 font-mono text-sm text-slate-300">{s.domain}</p>
            <p className="mt-2 text-sm text-slate-400">{s.reason}</p>
            {/* 사용자가 명시적으로 선택했을 때만 이동 */}
            <a
              href={s.url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 block rounded-lg bg-emerald-500 py-2 text-center font-semibold text-slate-950"
            >
              {s.domain}로 이동
            </a>
          </li>
        ))}
      </ul>

      <div className="mt-auto">
        <Button variant="secondary" onClick={goHome}>
          다시 스캔
        </Button>
      </div>
    </div>
  )
}
