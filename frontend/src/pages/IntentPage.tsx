import { useState } from 'react'
import { Navigate, useNavigate, useParams } from 'react-router'
import { ApiError, api } from '../api'
import { CautionSummaryModal } from '../components/CautionSummaryModal'
import { Button, ErrorView, LoadingView } from '../components/ui'
import { useAnalysis } from '../hooks/useAnalysis'
import { errorMessage } from '../lib/errors'
import { riskTier } from '../lib/verdict'
import { useScanFlow } from '../state/useScanFlow'

// 다시 입력할 수 없는 오류: 세션 만료·4~6점이 아닌 분석 → 결과 화면에서 기존 판정을 따른다
const FATAL_ERRORS = new Set(['ANALYSIS_NOT_FOUND', 'INTENT_GUIDANCE_NOT_ALLOWED'])

// SCR-005 접속 의도 확인: 4~6점(ASK_INTENT) 분석 직후 로딩 화면 위에 Caution summary 모달을 띄우고,
// 목적을 받아 AI 로 2차 검증한 뒤 결과 화면으로 보낸다 (사칭이면 결과 화면이 차단으로 바뀐다)
export function IntentPage() {
  const navigate = useNavigate()
  const { analysisId } = useParams()
  const { analysis, error: loadError } = useAnalysis(analysisId)
  const { setGuidance, reset } = useScanFlow()
  const [submitting, setSubmitting] = useState(false)
  const [notice, setNotice] = useState<{ tone: 'question' | 'error'; text: string } | null>(null)

  if (loadError) {
    return (
      <ErrorView title="분석 결과를 불러오지 못했어요" message={errorMessage(loadError)}>
        <Button
          onClick={() => {
            reset()
            navigate('/', { replace: true })
          }}
        >
          다시 스캔
        </Button>
      </ErrorView>
    )
  }
  if (!analysis) return <LoadingView title="분석 결과를 불러오고 있어요" />

  const resultPath = `/result/${encodeURIComponent(analysis.analysisId)}`

  // API-AC-04: 4~6점 결과에서만 의도 안내를 쓴다
  if (riskTier(analysis) !== 'AMBIGUOUS') return <Navigate to={resultPath} replace />

  // 입력을 비워야 하면 true 를 돌려준다
  const submit = async (userMessage: string): Promise<boolean> => {
    setSubmitting(true)
    setNotice(null)
    try {
      const guidance = await api.createIntentGuidance({ analysisId: analysis.analysisId, userMessage })
      if (guidance.guidanceStatus === 'NEEDS_CLARIFICATION') {
        setNotice({
          tone: 'question',
          text: guidance.followUpQuestion ?? '어떤 서비스에서 무엇을 하려는지 조금 더 자세히 알려 주세요.',
        })
        return true
      }
      setGuidance(guidance)
      navigate(resultPath, { replace: true })
      return false
    } catch (err) {
      if (err instanceof ApiError && FATAL_ERRORS.has(err.code)) {
        navigate(resultPath, { replace: true })
        return false
      }
      setNotice({ tone: 'error', text: errorMessage(err) })
      // 민감정보가 탐지되면 입력을 바로 폐기한다
      return err instanceof ApiError && err.code === 'SENSITIVE_DATA_DETECTED'
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <LoadingView title="피싱 의심 신호를 찾았어요" message="목적을 알려 주시면 AI가 한 번 더 확인해요" />
      <CautionSummaryModal
        score={analysis.score}
        submitting={submitting}
        notice={notice}
        onSubmit={submit}
        onSkip={() => navigate(resultPath, { replace: true })}
      />
    </>
  )
}
