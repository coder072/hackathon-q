import { useEffect, useState } from 'react'
import { api } from '../api'
import { useScanFlow } from '../state/useScanFlow'

// 흐름 상태에 같은 분석이 있으면 그대로 쓰고, 새로고침 등으로 없으면 GET /analyses/{id} 로 복원한다
export function useAnalysis(analysisId: string | undefined) {
  const { analysis, setAnalysis } = useScanFlow()
  const cached = analysis && analysis.analysisId === analysisId ? analysis : null
  const [error, setError] = useState<unknown>(null)
  const hasCached = cached !== null

  useEffect(() => {
    if (hasCached || !analysisId) return
    const controller = new AbortController()
    api
      .getAnalysis(analysisId, controller.signal)
      .then(setAnalysis)
      .catch((err: unknown) => {
        if (!controller.signal.aborted) setError(err)
      })
    return () => controller.abort()
  }, [analysisId, hasCached, setAnalysis])

  return { analysis: cached, error }
}
