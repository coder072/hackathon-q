import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router'
import { ReportForm } from '../components/ReportForm'
import { ResultScreen } from '../components/ResultScreen'
import { riskTier } from '../lib/verdict'
import { useScanFlow } from '../state/useScanFlow'

// SCR-003 안전 결과 / SCR-004 주의·차단 결과
export function ResultPage() {
  const navigate = useNavigate()
  const { analysis, reset } = useScanFlow()
  const [reportOpen, setReportOpen] = useState(false)

  if (!analysis) return <Navigate to="/" replace />

  const tier = riskTier(analysis)

  const rescan = () => {
    reset()
    navigate('/', { replace: true })
  }
  // RST-005: 명시적 버튼 선택 시에만 링크를 연다
  const openLink = () => window.open(analysis.finalUrl, '_blank', 'noopener,noreferrer')

  const actions: Record<typeof tier, { primary: () => void; secondary: () => void }> = {
    SAFE: { primary: openLink, secondary: rescan },
    AMBIGUOUS: { primary: rescan, secondary: openLink },
    HIGH: { primary: rescan, secondary: () => setReportOpen(true) },
  }

  return (
    <ResultScreen
      analysis={analysis}
      tier={tier}
      onBack={() => navigate(-1)}
      onClose={rescan}
      onPrimaryAction={actions[tier].primary}
      onSecondaryAction={actions[tier].secondary}
    >
      {tier === 'AMBIGUOUS' && (
        <button
          type="button"
          onClick={() => navigate('/intent')}
          className="py-2 text-center text-sm text-[#a9acae] underline underline-offset-4"
        >
          원래 가려던 공식 사이트 찾기
        </button>
      )}
      {(tier === 'AMBIGUOUS' || (tier === 'HIGH' && reportOpen)) && <ReportForm analysisId={analysis.analysisId} />}
    </ResultScreen>
  )
}
