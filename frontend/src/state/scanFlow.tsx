import { useMemo, useState, type ReactNode } from 'react'
import { ScanFlowContext, type ScanFlowContextValue, type ScanFlowState } from './useScanFlow'

const initialState: ScanFlowState = { scannedUrl: null, analysis: null, guidance: null }

export function ScanFlowProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState(initialState)

  // 액션은 참조가 바뀌지 않도록 고정 (effect 의존성으로 써도 재실행되지 않게)
  const actions = useMemo<Omit<ScanFlowContextValue, keyof ScanFlowState>>(
    () => ({
      setScannedUrl: (scannedUrl) => setState({ ...initialState, scannedUrl }),
      setAnalysis: (analysis) => setState((s) => ({ ...s, analysis, guidance: null })),
      setGuidance: (guidance) => setState((s) => ({ ...s, guidance })),
      reset: () => setState(initialState),
    }),
    [],
  )
  const value = useMemo<ScanFlowContextValue>(() => ({ ...state, ...actions }), [state, actions])

  return <ScanFlowContext value={value}>{children}</ScanFlowContext>
}
