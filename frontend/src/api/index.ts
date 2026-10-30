import { request } from './client'
import type {
  AnalysisRequest,
  AnalysisResult,
  HealthStatus,
  IntentGuidance,
  IntentGuidanceRequest,
  ReportCreated,
  ReportRequest,
} from './types'

export { ApiError } from './client'
export type * from './types'

export const api = {
  health: (signal?: AbortSignal) => request<HealthStatus>('/health', { signal }),

  createAnalysis: (body: AnalysisRequest, signal?: AbortSignal) =>
    request<AnalysisResult>('/analyses', { method: 'POST', body, signal }),

  getAnalysis: (analysisId: string, signal?: AbortSignal) =>
    request<AnalysisResult>(`/analyses/${encodeURIComponent(analysisId)}`, { signal }),

  createIntentGuidance: (body: IntentGuidanceRequest, signal?: AbortSignal) =>
    request<IntentGuidance>('/intent-guidance', { method: 'POST', body, signal }),

  createReport: (body: ReportRequest, signal?: AbortSignal) =>
    request<ReportCreated>('/reports', { method: 'POST', body, signal }),
}
