import { useMemo, useState, type ReactNode } from 'react'
import type { IntentGuidance } from '../api'
import { ScanFlowContext, type ScanFlowContextValue, type ScanFlowState } from './useScanFlow'

// 결과 화면을 새로고침해도 AI 2차 검증 판정(주의/차단)이 유지되도록 탭 단위로 보관한다.
// 서버 응답만 저장하며 사용자가 입력한 목적 원문은 들어 있지 않다.
const GUIDANCE_KEY = 'scanFlow.guidance'

function loadGuidance(): IntentGuidance | null {
  try {
    const raw = sessionStorage.getItem(GUIDANCE_KEY)
    return raw ? (JSON.parse(raw) as IntentGuidance) : null
  } catch {
    return null
  }
}

function saveGuidance(guidance: IntentGuidance | null) {
  try {
    if (guidance) sessionStorage.setItem(GUIDANCE_KEY, JSON.stringify(guidance))
    else sessionStorage.removeItem(GUIDANCE_KEY)
  } catch {
    // 저장소를 쓸 수 없으면 새로고침 시 판정만 사라진다
  }
}

const initialState: ScanFlowState = { scannedUrl: null, analysis: null, guidance: null }

export function ScanFlowProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<ScanFlowState>(() => ({ ...initialState, guidance: loadGuidance() }))

  // 액션은 참조가 바뀌지 않도록 고정 (effect 의존성으로 써도 재실행되지 않게)
  const actions = useMemo<Omit<ScanFlowContextValue, keyof ScanFlowState>>(
    () => ({
      setScannedUrl: (scannedUrl) => {
        saveGuidance(null)
        setState({ ...initialState, scannedUrl })
      },
      // 같은 분석의 판정은 남긴다 (새로고침 후 분석을 다시 불러오는 경우)
      setAnalysis: (analysis) =>
        setState((s) => ({ ...s, analysis, guidance: s.guidance?.analysisId === analysis.analysisId ? s.guidance : null })),
      setGuidance: (guidance) => {
        saveGuidance(guidance)
        setState((s) => ({ ...s, guidance }))
      },
      reset: () => {
        saveGuidance(null)
        setState(initialState)
      },
    }),
    [],
  )
  const value = useMemo<ScanFlowContextValue>(() => ({ ...state, ...actions }), [state, actions])

  return <ScanFlowContext value={value}>{children}</ScanFlowContext>
}
