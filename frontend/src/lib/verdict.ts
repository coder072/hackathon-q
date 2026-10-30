import type { AnalysisResult } from '../api'

// 명세 5. 위험 점수 기준
export type RiskTier = 'SAFE' | 'AMBIGUOUS' | 'HIGH'

export function riskTier({ verdict, score }: Pick<AnalysisResult, 'verdict' | 'score'>): RiskTier {
  if (verdict === 'SAFE') return 'SAFE'
  // RST-006: 4~6점은 의도 확인 대상, 7~10점(차단 목록 포함)은 강한 경고
  return score <= 6 ? 'AMBIGUOUS' : 'HIGH'
}

export function isHttpUrl(text: string): boolean {
  try {
    const { protocol } = new URL(text.trim())
    return protocol === 'http:' || protocol === 'https:'
  } catch {
    return false
  }
}
