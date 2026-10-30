import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate, useParams } from 'react-router'
import { ApiError, api } from '../api'
import { Button, ErrorView, LoadingView, StatusBadge } from '../components/ui'
import { useAnalysis } from '../hooks/useAnalysis'
import { errorMessage } from '../lib/errors'
import { riskTier } from '../lib/verdict'
import { useScanFlow } from '../state/useScanFlow'

const MAX_LENGTH = 300
const EXAMPLES = ['네이버 로그인하려고', '택배 배송 조회', '카드 결제하려고']

// 다시 입력할 수 없는 오류: 세션 만료·4~6점이 아닌 분석
const FATAL_ERRORS = new Set(['ANALYSIS_NOT_FOUND', 'INTENT_GUIDANCE_NOT_ALLOWED'])

// SCR-005 접속 의도 확인 화면: 4~6점(ASK_INTENT)에서 목적을 받아 AI 로 2차 검증한다
export function IntentPage() {
  const navigate = useNavigate()
  const { analysisId } = useParams()
  const { analysis, error: loadError } = useAnalysis(analysisId)
  const { setGuidance, reset } = useScanFlow()
  const [message, setMessage] = useState('')
  const [followUp, setFollowUp] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<unknown>(null)

  const goHome = () => {
    reset()
    navigate('/', { replace: true })
  }

  if (loadError) {
    return (
      <ErrorView title="분석 결과를 불러오지 못했어요" message={errorMessage(loadError)}>
        <Button onClick={goHome}>다시 스캔</Button>
      </ErrorView>
    )
  }
  if (!analysis) return <LoadingView title="분석 결과를 불러오고 있어요" />

  const resultPath = `/result/${encodeURIComponent(analysis.analysisId)}`

  // API-AC-04: 4~6점 결과에서만 의도 안내를 쓴다
  if (riskTier(analysis) !== 'AMBIGUOUS') return <Navigate to={resultPath} replace />

  const signals = analysis.checks.filter((c) => c.detected && c.score > 0)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const userMessage = message.trim()
    if (!userMessage) return
    setSubmitting(true)
    setError(null)
    try {
      const guidance = await api.createIntentGuidance({ analysisId: analysis.analysisId, userMessage })
      if (guidance.guidanceStatus === 'NEEDS_CLARIFICATION') {
        setFollowUp(guidance.followUpQuestion ?? '어떤 서비스에서 무엇을 하려는지 조금 더 자세히 알려 주세요.')
        return
      }
      setGuidance(guidance)
      navigate(resultPath)
    } catch (err) {
      // 민감정보가 탐지되면 입력을 바로 폐기한다
      if (err instanceof ApiError && err.code === 'SENSITIVE_DATA_DETECTED') setMessage('')
      setError(err)
    } finally {
      setSubmitting(false)
    }
  }

  if (error instanceof ApiError && FATAL_ERRORS.has(error.code)) {
    return (
      <ErrorView title="원래 링크는 계속 차단돼요" message={errorMessage(error)}>
        <Button onClick={goHome}>다시 스캔</Button>
        <Button variant="secondary" onClick={() => navigate(resultPath, { replace: true })}>
          분석 결과 보기
        </Button>
      </ErrorView>
    )
  }

  if (submitting) {
    return <LoadingView title="AI가 목적을 확인하고 있어요" message="확인된 공식 사이트만 찾아서 안내해 드릴게요" />
  }

  return (
    <form onSubmit={submit} className="flex flex-1 flex-col gap-4 py-6">
      <StatusBadge tone="warn" icon="⚠️">
        피싱이 의심되는 링크예요
      </StatusBadge>

      <section className="rounded-xl bg-slate-900 p-4 text-sm">
        <div className="flex items-baseline justify-between gap-3">
          <p className="min-w-0 truncate font-mono text-slate-300">{analysis.displayDomain}</p>
          <p className="shrink-0 font-semibold text-amber-300">위험 신호 {analysis.score} / 10</p>
        </div>
        {signals.length > 0 && (
          <ul className="mt-3 list-disc space-y-1 pl-5 text-slate-400">
            {signals.map((c) => (
              <li key={c.code}>{c.message}</li>
            ))}
          </ul>
        )}
        <p className="mt-3 text-slate-400">원래 링크는 열지 않고 막아 두었어요.</p>
      </section>

      <div>
        <h1 className="text-xl font-bold">이 QR 코드를 어떤 목적으로 스캔하셨나요?</h1>
        <p className="mt-1 text-sm text-slate-400">목적을 알려 주시면 AI가 확인한 뒤, 검증된 공식 사이트로 안내해 드릴게요.</p>
      </div>

      {followUp && (
        <p role="status" className="rounded-xl bg-sky-500/15 p-3 text-sm text-sky-200 ring-1 ring-sky-500/40">
          💬 {followUp}
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            type="button"
            className="rounded-full bg-slate-800 px-3 py-1 text-sm text-slate-300"
            onClick={() => setMessage(ex)}
          >
            {ex}
          </button>
        ))}
      </div>

      <textarea
        className="min-h-28 rounded-xl bg-slate-900 p-3 text-base outline-none focus:ring-2 focus:ring-emerald-500"
        placeholder="예: 쿠팡에서 주문 내역 보려고"
        maxLength={MAX_LENGTH}
        value={message}
        onChange={(e) => setMessage(e.target.value)}
      />
      <p className="-mt-2 text-right text-xs text-slate-500">
        {message.length}/{MAX_LENGTH}
      </p>

      {error !== null && (
        <p role="alert" className="rounded-xl bg-red-500/15 p-3 text-sm text-red-200 ring-1 ring-red-500/40">
          {errorMessage(error)}
        </p>
      )}

      <p role="note" className="rounded-xl bg-amber-500/15 p-3 text-sm text-amber-200 ring-1 ring-amber-500/40">
        🔒 비밀번호, 인증번호, 계좌번호, 주민등록번호 등 민감한 정보는 절대 입력하지 마세요.
      </p>

      <div className="mt-auto flex flex-col gap-2">
        <Button type="submit" disabled={!message.trim()}>
          공식 사이트 찾기
        </Button>
        <Button type="button" variant="secondary" onClick={() => navigate(resultPath)}>
          입력하지 않고 결과 보기
        </Button>
      </div>
    </form>
  )
}
