// API 명세서 기준 타입 (응답 JSON 은 camelCase)

export type Verdict = 'SAFE' | 'SUSPICIOUS'

export type RecommendedAction = 'OPEN_ALLOWED' | 'ASK_INTENT' | 'BLOCK'

export type CheckCode =
  | 'HTTPS_NOT_USED'
  | 'LOOKALIKE_DOMAIN'
  | 'SUSPICIOUS_URL_STRUCTURE'
  | 'DIRECT_IP_ACCESS'
  | 'EXCESSIVE_REDIRECTS'
  | 'NEW_DOMAIN'
  | 'SUSPICIOUS_TLD'
  // 명세 MVP 표에는 없지만 현재 백엔드가 함께 내려준다
  | 'BLOCKLIST_MATCH'
  | 'ALLOWLIST_MATCH'

export interface ApiSuccess<T> {
  success: true
  data: T
  requestId: string | null
}

export interface ApiErrorBody {
  success: false
  error: {
    code: ErrorCode
    message: string
    details: unknown[]
  }
  requestId: string | null
}

export type ErrorCode =
  | 'INVALID_REQUEST'
  | 'INVALID_URL'
  | 'UNSUPPORTED_SCHEME'
  | 'URL_TOO_LONG'
  | 'PRIVATE_NETWORK_TARGET'
  | 'DNS_RESOLUTION_FAILED'
  | 'REDIRECT_LIMIT_EXCEEDED'
  | 'RATE_LIMIT_EXCEEDED'
  | 'ANALYSIS_FAILED'
  | 'ANALYSIS_TIMEOUT'
  | 'ANALYSIS_NOT_FOUND'
  | 'INVALID_INTENT_MESSAGE'
  | 'INTENT_GUIDANCE_NOT_ALLOWED'
  | 'SENSITIVE_DATA_DETECTED'
  | 'INTENT_SERVICE_UNAVAILABLE'
  // 클라이언트 전용: 네트워크 단절, 응답 파싱 실패
  | 'NETWORK_ERROR'
  | 'UNKNOWN_ERROR'

// POST /analyses
export interface AnalysisRequest {
  url: string
  clientRequestId?: string
}

export interface CheckResult {
  code: CheckCode
  detected: boolean
  score: number
  message: string
}

export interface AnalysisResult {
  analysisId: string
  verdict: Verdict
  score: number
  recommendedAction: RecommendedAction
  originalUrl: string
  finalUrl: string
  displayDomain: string
  redirectCount: number
  checks: CheckResult[]
  analyzedAt: string
  expiresAt: string
}

// POST /intent-guidance
export interface IntentGuidanceRequest {
  analysisId: string
  userMessage: string
}

export type GuidanceStatus = 'MATCHED' | 'NEEDS_CLARIFICATION' | 'NOT_FOUND'

export interface OfficialSiteSuggestion {
  name: string
  url: string
  domain: string
  reason: string
  verified: true
}

// QR 링크와 사용자 의도를 비교한 AI 2차 검증 결과 (명세 이후 백엔드에 추가된 필드)
export interface IntentAssessment {
  matchesIntent: boolean | null
  explanation: string
  source: 'llm' | 'rules'
}

export interface IntentGuidance {
  analysisId: string
  assessment?: IntentAssessment
  guidanceStatus: GuidanceStatus
  intentCode: string | null
  serviceKey: string | null
  serviceName: string | null
  confidence: number
  followUpQuestion: string | null
  suggestions: OfficialSiteSuggestion[]
}

// GET /health
export interface HealthStatus {
  status: 'UP' | 'DEGRADED'
  version: string
  timestamp: string
}
