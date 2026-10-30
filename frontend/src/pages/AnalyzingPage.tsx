import { useEffect, useState } from 'react'
import { Navigate, useNavigate } from 'react-router'
import { api } from '../api'
import { Button, ErrorView } from '../components/ui'
import { errorMessage } from '../lib/errors'
import { useOnlineStatus } from '../hooks/useOnlineStatus'
import { useScanFlow } from '../state/useScanFlow'

// SCR-002 분석 중 화면
export function AnalyzingPage() {
  const navigate = useNavigate()
  const { scannedUrl, setAnalysis } = useScanFlow()
  const online = useOnlineStatus()
  const [error, setError] = useState<unknown>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!scannedUrl || !online) return
    const controller = new AbortController()

    api
      .createAnalysis({ url: scannedUrl, source: 'CAMERA', clientRequestId: crypto.randomUUID() }, controller.signal)
      .then((result) => {
        setAnalysis(result)
        navigate('/result', { replace: true })
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return
        // NFR-004: 실패는 절대 안전으로 처리하지 않는다
        setError(err)
      })

    return () => controller.abort()
  }, [scannedUrl, online, attempt, navigate, setAnalysis])

  if (!scannedUrl) return <Navigate to="/" replace />

  if (!online) {
    return (
      <ErrorView
        title="오프라인에서는 분석할 수 없어요"
        message="네트워크 연결을 확인해 주세요. 연결되면 안전 판정 없이 분석을 다시 시작합니다."
      >
        <Button variant="secondary" onClick={() => navigate('/', { replace: true })}>
          다시 스캔
        </Button>
      </ErrorView>
    )
  }

  if (error) {
    return (
      <ErrorView title="분석하지 못했어요" message={errorMessage(error)}>
        <Button
          onClick={() => {
            setError(null)
            setAttempt((n) => n + 1)
          }}
        >
          다시 시도
        </Button>
        <Button variant="secondary" onClick={() => navigate('/', { replace: true })}>
          다시 스캔
        </Button>
      </ErrorView>
    )
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6 py-8 text-center">
      <div className="size-12 animate-spin rounded-full border-4 border-slate-700 border-t-emerald-400" aria-hidden />
      <div>
        <p className="text-lg font-semibold">링크를 분석하고 있어요</p>
        <p className="mt-1 text-sm text-slate-400">주소 형식 · 리디렉션 · 유사 도메인 · 차단 목록 확인 중</p>
      </div>
      <p className="max-w-full truncate rounded-lg bg-slate-900 px-3 py-2 font-mono text-xs text-slate-400">{scannedUrl}</p>
      <Button variant="secondary" onClick={() => navigate('/', { replace: true })}>
        취소
      </Button>
    </div>
  )
}
