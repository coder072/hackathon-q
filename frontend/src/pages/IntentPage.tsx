import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router'
import { api } from '../api'
import { Button, ErrorView } from '../components/ui'
import { errorMessage } from '../lib/errors'
import { riskTier } from '../lib/verdict'
import { useScanFlow } from '../state/useScanFlow'

const MAX_LENGTH = 300
const EXAMPLES = ['네이버 로그인하려고', '택배 배송 조회', '카드 결제하려고']

// SCR-005 접속 의도 확인 화면 (INT-001, INT-005)
export function IntentPage() {
  const navigate = useNavigate()
  const { analysis, setGuidance, reset } = useScanFlow()
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<unknown>(null)

  // 4~6점 결과에서만 진입 가능
  if (!analysis || riskTier(analysis) !== 'AMBIGUOUS') return <Navigate to="/" replace />

  const goHome = () => {
    reset()
    navigate('/', { replace: true })
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const userMessage = message.trim()
    if (!userMessage) return
    setSubmitting(true)
    setError(null)
    try {
      const guidance = await api.createIntentGuidance({ analysisId: analysis.analysisId, userMessage })
      setGuidance(guidance)
      navigate('/suggestions')
    } catch (err) {
      setError(err)
    } finally {
      setSubmitting(false)
    }
  }

  if (error) {
    // RST-010: 의도 불명 / 후보 없음이면 차단 유지 + 제공처 확인·재스캔 안내
    return (
      <ErrorView title="원래 링크는 계속 차단돼요" message={errorMessage(error)}>
        <Button onClick={() => setError(null)}>다시 입력</Button>
        <Button variant="secondary" onClick={goHome}>
          다시 스캔
        </Button>
      </ErrorView>
    )
  }

  return (
    <form onSubmit={submit} className="flex flex-1 flex-col gap-4 py-6">
      <h1 className="text-xl font-bold">이 QR 코드를 어떤 목적으로 스캔하셨나요?</h1>
      <p className="text-sm text-slate-400">원래 링크 대신, 확인된 공식 사이트를 찾아 안내해 드릴게요.</p>

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

      <p role="note" className="rounded-xl bg-amber-500/15 p-3 text-sm text-amber-200 ring-1 ring-amber-500/40">
        🔒 비밀번호, 인증번호, 계좌번호, 주민등록번호 등 민감한 정보는 절대 입력하지 마세요.
      </p>

      <div className="mt-auto flex flex-col gap-2">
        <Button type="submit" disabled={submitting || !message.trim()}>
          {submitting ? '확인 중…' : '공식 사이트 찾기'}
        </Button>
        <Button type="button" variant="secondary" onClick={goHome}>
          돌아가기
        </Button>
      </div>
    </form>
  )
}
