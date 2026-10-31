import { useEffect, useState } from 'react'
import { Navigate, useNavigate } from 'react-router'
import { ApiError, api, type ErrorCode } from '../api'
import { AnalysisFailedView, AnalyzingView } from '../components/AnalysisScreens'
import { Button } from '../components/ui'
import { errorMessage } from '../lib/errors'
import { nextPath } from '../lib/verdict'
import { useScanFlow } from '../state/useScanFlow'

// 다시 분석해도 결과가 같은 오류: 주소 자체가 분석 대상이 아니다
const NOT_RETRYABLE = new Set<ErrorCode>([
  'INVALID_REQUEST',
  'INVALID_URL',
  'UNSUPPORTED_SCHEME',
  'URL_TOO_LONG',
  'PRIVATE_NETWORK_TARGET',
  'REDIRECT_LIMIT_EXCEEDED',
])

// SCR-002 분석 중 화면: 위험 점수에 따라 결과(0~3·7~10점) 또는 목적 입력(4~6점)으로 보낸다
export function AnalyzingPage() {
  const navigate = useNavigate()
  const { scannedUrl, setAnalysis, reset } = useScanFlow()
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

  const goHome = () => {
    reset()
    navigate('/', { replace: true })
  }

  if (error) {
    const retryable = !(error instanceof ApiError && NOT_RETRYABLE.has(error.code))
    return (
      <AnalysisFailedView
        url={scannedUrl}
        causeTitle={retryable ? '잠시 후 다시 시도해주세요' : '이 주소는 분석할 수 없어요'}
        causeMessage={errorMessage(error)}
        onBack={goHome}
        onClose={goHome}
      >
        {retryable ? (
          <>
            <Button
              onClick={() => {
                setError(null)
                setAttempt((n) => n + 1)
              }}
            >
              다시 분석하기
            </Button>
            <Button variant="secondary" onClick={goHome}>
              처음으로
            </Button>
          </>
        ) : (
          <Button onClick={goHome}>다시 스캔</Button>
        )}
      </AnalysisFailedView>
    )
  }

  return <AnalyzingView key={attempt} url={scannedUrl} onBack={goHome} onClose={goHome} />
}
