import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { GuidanceCard } from '../components/GuidanceCard'
import { ReportGuide } from '../components/ReportGuide'
import { ResultScreen } from '../components/ResultScreen'
import { Button, ErrorView, LoadingView } from '../components/ui'
import { useAnalysis } from '../hooks/useAnalysis'
import { errorMessage } from '../lib/errors'
import { riskTier } from '../lib/verdict'
import { useScanFlow } from '../state/useScanFlow'

// SCR-003 안전 결과(0~3점) / SCR-004 주의 결과(4~6점, AI 2차 검증 후)·차단 결과(7~10점)
export function ResultPage() {
  const navigate = useNavigate()
  const { analysisId } = useParams()
  const { analysis, error } = useAnalysis(analysisId)
  const { guidance, reset } = useScanFlow()
  const [reportOpen, setReportOpen] = useState(false)

  const rescan = () => {
    reset()
    navigate('/', { replace: true })
  }

  if (error) {
    return (
      <ErrorView title="분석 결과를 불러오지 못했어요" message={errorMessage(error)}>
        <Button onClick={rescan}>다시 스캔</Button>
      </ErrorView>
    )
  }
  if (!analysis) return <LoadingView title="분석 결과를 불러오고 있어요" />

  const tier = riskTier(analysis)
  const currentGuidance = guidance?.analysisId === analysis.analysisId ? guidance : null
  const toIntent = () => navigate(`/intent/${encodeURIComponent(analysis.analysisId)}`)
  // RST-005: 명시적 버튼 선택 시에만 링크를 연다. 4~6점·7~10점은 원본 링크를 열지 않는다.
  const openLink = () => window.open(analysis.finalUrl, '_blank', 'noopener,noreferrer')

  const actions: Record<typeof tier, { primary: () => void; secondary: () => void; secondaryLabel?: string }> = {
    SAFE: { primary: openLink, secondary: rescan },
    AMBIGUOUS: {
      primary: rescan,
      secondary: toIntent,
      secondaryLabel: currentGuidance ? undefined : '목적 입력하고 공식 사이트 찾기',
    },
    HIGH: { primary: rescan, secondary: () => setReportOpen((open) => !open) },
  }

  return (
    <ResultScreen
      analysis={analysis}
      tier={tier}
      // 새로고침·직접 진입이면 history 가 없을 수 있어 경로를 명시한다
      onBack={tier === 'AMBIGUOUS' ? toIntent : rescan}
      onClose={rescan}
      onPrimaryAction={actions[tier].primary}
      onSecondaryAction={actions[tier].secondary}
      secondaryLabel={actions[tier].secondaryLabel}
    >
      {tier === 'AMBIGUOUS' && currentGuidance && <GuidanceCard guidance={currentGuidance} />}
      {tier === 'HIGH' && reportOpen && <ReportGuide />}
    </ResultScreen>
  )
}
