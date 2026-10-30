import { useEffect, useState } from 'react'
import { Navigate, useNavigate } from 'react-router'
import { api } from '../api'
import { Button, ErrorView, LoadingView } from '../components/ui'
import { errorMessage } from '../lib/errors'
import { nextPath } from '../lib/verdict'
import { useScanFlow } from '../state/useScanFlow'

// SCR-002 분석 중 화면: 위험 점수에 따라 결과(0~3·7~10점) 또는 목적 입력(4~6점)으로 보낸다
export function AnalyzingPage() {
  const navigate = useNavigate()
  const { scannedUrl, setAnalysis } = useScanFlow()
  const [error, setError] = useState<unknown>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!scannedUrl) return
    const controller = new AbortController()

    api
      .createAnalysis({ url: scannedUrl, clientRequestId: crypto.randomUUID() }, controller.signal)
      .then((result) => {
        setAnalysis(result)
        navigate(nextPath(result), { replace: true })
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return
        // API-AC-03: 실패는 절대 안전으로 처리하지 않는다
        setError(err)
      })

    return () => controller.abort()
  }, [scannedUrl, attempt, navigate, setAnalysis])

  if (!scannedUrl) return <Navigate to="/" replace />

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
    <LoadingView title="링크를 분석하고 있어요" message="통신 보안 · 유사 도메인 · 주소 구조 · 리디렉션 확인 중">
      <p className="max-w-full truncate rounded-lg bg-slate-900 px-3 py-2 font-mono text-xs text-slate-400">{scannedUrl}</p>
      <Button variant="secondary" onClick={() => navigate('/', { replace: true })}>
        취소
      </Button>
    </LoadingView>
  )
}
