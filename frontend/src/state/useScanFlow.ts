import { createContext, use } from 'react'
import type { AnalysisResult, IntentGuidance } from '../api'

// 스캔 → 분석 → 결과 → 의도 확인 → 공식 사이트 추천 흐름에서 화면 간 공유하는 상태
export interface ScanFlowState {
  scannedUrl: string | null
  analysis: AnalysisResult | null
  guidance: IntentGuidance | null
}

export interface ScanFlowContextValue extends ScanFlowState {
  setScannedUrl: (url: string) => void
  setAnalysis: (analysis: AnalysisResult) => void
  setGuidance: (guidance: IntentGuidance) => void
  reset: () => void
}

export const ScanFlowContext = createContext<ScanFlowContextValue | null>(null)

export function useScanFlow() {
  const ctx = use(ScanFlowContext)
  if (!ctx) throw new Error('useScanFlow must be used within ScanFlowProvider')
  return ctx
}
