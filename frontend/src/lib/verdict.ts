import type { AnalysisResult, RecommendedAction } from '../api'

// 명세 "위험 점수" 기준: 0~3 OPEN_ALLOWED, 4~6 ASK_INTENT, 7~10 BLOCK
export type RiskTier = 'SAFE' | 'AMBIGUOUS' | 'HIGH'

const TIERS: Record<RecommendedAction, RiskTier> = {
  OPEN_ALLOWED: 'SAFE',
  ASK_INTENT: 'AMBIGUOUS',
  BLOCK: 'HIGH',
}

// 점수 구간을 다시 계산하지 않고 서버가 정한 권장 행동을 따른다. 모르는 값은 차단으로 본다.
export function riskTier({ recommendedAction }: Pick<AnalysisResult, 'recommendedAction'>): RiskTier {
  return TIERS[recommendedAction] ?? 'HIGH'
}

// 분석 직후 이동할 화면: 4~6점은 결과 대신 목적 입력으로 보낸다
export function nextPath(analysis: AnalysisResult): string {
  const id = encodeURIComponent(analysis.analysisId)
  return riskTier(analysis) === 'AMBIGUOUS' ? `/intent/${id}` : `/result/${id}`
}

export function isHttpUrl(text: string): boolean {
  try {
    const { protocol } = new URL(text.trim())
    return protocol === 'http:' || protocol === 'https:'
  } catch {
    return false
  }
}
