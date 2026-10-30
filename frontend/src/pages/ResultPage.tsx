import { Navigate, useNavigate } from 'react-router'
import type { AnalysisResult } from '../api'
import { ReportForm } from '../components/ReportForm'
import { Button, StatusBadge } from '../components/ui'
import { riskTier } from '../lib/verdict'
import { useScanFlow } from '../state/useScanFlow'

// SCR-003 안전 결과 / SCR-004 피싱 의심 결과
export function ResultPage() {
  const navigate = useNavigate()
  const { analysis, reset } = useScanFlow()

  if (!analysis) return <Navigate to="/" replace />

  const tier = riskTier(analysis)
  const rescan = () => {
    reset()
    navigate('/', { replace: true })
  }

  if (tier === 'SAFE') {
    return (
      <div className="flex flex-1 flex-col gap-5 py-6">
        <StatusBadge tone="safe" icon="✅">
          안전
        </StatusBadge>
        <Destination analysis={analysis} />
        <Reasons analysis={analysis} />
        <p className="text-xs text-slate-500">위험 신호가 발견되지 않았다는 의미이며, 절대적인 안전을 보장하지는 않아요.</p>
        <div className="mt-auto flex flex-col gap-2">
          {/* RST-005: 명시적 버튼 선택 시에만 링크를 연다 */}
          <Button onClick={() => window.open(analysis.finalUrl, '_blank', 'noopener,noreferrer')}>링크 열기</Button>
          <Button variant="secondary" onClick={rescan}>
            다시 스캔
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col gap-5 py-6">
      <StatusBadge tone="danger" icon="🚫">
        피싱 의심
      </StatusBadge>
      {tier === 'HIGH' && (
        <p role="alert" className="rounded-xl bg-red-500/20 p-3 font-semibold text-red-200">
          이 링크는 열지 마세요. 개인정보나 금융정보를 탈취하려는 사이트일 가능성이 높아요.
        </p>
      )}
      <Reasons analysis={analysis} />
      <Destination analysis={analysis} />
      <div className="mt-auto flex flex-col gap-2">
        {/* RST-004: 기본 동작은 돌아가기. 원래 링크를 여는 버튼은 제공하지 않는다 */}
        <Button onClick={rescan}>돌아가기</Button>
        {tier === 'AMBIGUOUS' && (
          <Button variant="secondary" onClick={() => navigate('/intent')}>
            원래 가려던 공식 사이트 찾기
          </Button>
        )}
      </div>
      <ReportForm analysisId={analysis.analysisId} />
    </div>
  )
}

function Destination({ analysis }: { analysis: AnalysisResult }) {
  // RST-003: 접속 전 목적지 미리보기 (텍스트로만 표시, 링크로 만들지 않음)
  return (
    <dl className="space-y-3 rounded-xl bg-slate-900 p-4 text-sm">
      <div>
        <dt className="text-slate-400">목적지 도메인</dt>
        <dd className="text-base font-semibold break-all">{analysis.displayDomain}</dd>
      </div>
      <div>
        <dt className="text-slate-400">QR 속 주소</dt>
        <dd className="font-mono text-xs break-all">{analysis.originalUrl}</dd>
      </div>
      {analysis.redirectCount > 0 && (
        <div>
          <dt className="text-slate-400">최종 이동 주소 (리디렉션 {analysis.redirectCount}회)</dt>
          <dd className="font-mono text-xs break-all">{analysis.finalUrl}</dd>
        </div>
      )}
    </dl>
  )
}

function Reasons({ analysis }: { analysis: AnalysisResult }) {
  const detected = analysis.checks.filter((c) => c.detected && c.score > 0)
  if (detected.length === 0) return null

  return (
    <section>
      <h2 className="mb-2 font-semibold">판정 근거</h2>
      <ul className="space-y-2">
        {detected.map((check) => (
          <li key={check.code} className="flex gap-2 rounded-lg bg-slate-900 p-3 text-sm">
            <span aria-hidden>⚠️</span>
            {check.message}
          </li>
        ))}
      </ul>
    </section>
  )
}
