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

  // QR 링크와 사용자 목적을 비교한 판단 (AI 또는 규칙). 원래 링크는 어떤 경우에도 열지 않는다
  const assessment = (
    <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100">
      <p className="mb-1 font-semibold">{guidance.assessment.source === 'llm' ? 'AI 판단' : '판단'}</p>
      <p>{guidance.assessment.explanation}</p>
    </div>
  )

  // RST-010: 의도를 알 수 없거나 후보가 없으면 원래 링크 차단을 유지한다
  if (suggestions.length === 0) {
    const needsMore = guidance.guidanceStatus === 'NEEDS_CLARIFICATION'
    return (
      <ErrorView
        title="원래 링크는 계속 차단돼요"
        message={
          needsMore && guidance.followUpQuestion
            ? guidance.followUpQuestion
            : '확인된 공식 사이트를 찾지 못했어요. QR을 제공한 곳에 직접 확인해 주세요.'
        }
      >
        {assessment}
        {needsMore && <Button onClick={() => navigate('/intent')}>다시 입력</Button>}
        <Button variant={needsMore ? 'secondary' : undefined} onClick={goHome}>
          다시 스캔
        </Button>
      </ErrorView>
    )
  }

  return (
    <div className="flex flex-1 flex-col gap-4 py-6">
      <div>
        <p className="text-sm text-slate-400">이렇게 이해했어요</p>
        <h1 className="text-xl font-bold">
          {guidance.serviceName} · {guidance.intentCode}
        </h1>
      </div>

      {assessment}

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
