import { useState } from 'react'
import { ApiError, api, type ReportReason } from '../api'
import { errorMessage } from '../lib/errors'

const REASONS: { value: ReportReason; label: string }[] = [
  { value: 'SUSPICIOUS_LOGIN', label: '로그인·개인정보 입력 요구' },
  { value: 'PAYMENT_REQUEST', label: '결제·송금 요구' },
  { value: 'IMPERSONATION', label: '기관·서비스 사칭' },
  { value: 'MALWARE', label: '앱·파일 설치 유도' },
  { value: 'OTHER', label: '기타' },
]

export function ReportForm({ analysisId }: { analysisId: string }) {
  const [reason, setReason] = useState<ReportReason>('SUSPICIOUS_LOGIN')
  const [status, setStatus] = useState<'idle' | 'sending' | 'done'>('idle')
  const [error, setError] = useState<string | null>(null)

  const submit = async () => {
    setStatus('sending')
    setError(null)
    try {
      await api.createReport({ analysisId, reason })
      setStatus('done')
    } catch (err) {
      if (err instanceof ApiError && err.code === 'REPORT_ALREADY_EXISTS') {
        setStatus('done')
        return
      }
      setError(errorMessage(err))
      setStatus('idle')
    }
  }

  if (status === 'done') return <p className="text-center text-sm text-slate-400">신고가 접수됐어요. 감사합니다.</p>

  return (
    <details className="rounded-xl bg-slate-900 p-4 text-sm">
      <summary className="cursor-pointer text-slate-300">이 QR 신고하기</summary>
      <div className="mt-3 flex gap-2">
        <select
          className="flex-1 rounded-lg bg-slate-800 px-3 py-2"
          value={reason}
          onChange={(e) => setReason(e.target.value as ReportReason)}
        >
          {REASONS.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </select>
        <button
          className="rounded-lg bg-slate-700 px-4 font-semibold disabled:opacity-50"
          disabled={status === 'sending'}
          onClick={submit}
        >
          신고
        </button>
      </div>
      {error && <p className="mt-2 text-red-300">{error}</p>}
    </details>
  )
}
