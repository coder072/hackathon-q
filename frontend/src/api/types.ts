// API 명세서 기준 타입 (응답 JSON 은 camelCase)

export type Verdict = 'SAFE' | 'SUSPICIOUS'

export type RecommendedAction = 'OPEN_ALLOWED' | 'ASK_INTENT' | 'BLOCK'

export type CheckCode =
  | 'HTTPS_NOT_USED'
  | 'LOOKALIKE_DOMAIN'
  | 'SUSPICIOUS_URL_STRUCTURE'
  | 'DIRECT_IP_ACCESS'
  | 'BLOCKLIST_MATCH'
  | 'EXCESSIVE_REDIRECTS'
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
  | 'REPORT_ALREADY_EXISTS'
  | 'INVALID_REPORT_REASON'
  | 'INVALID_INTENT_MESSAGE'
  | 'INTENT_GUIDANCE_NOT_ALLOWED'
  | 'SENSITIVE_DATA_DETECTED'
  // 클라이언트 전용: 네트워크 단절, 응답 파싱 실패
  | 'NETWORK_ERROR'
  | 'UNKNOWN_ERROR'

// POST /analyses
export type ScanSource = 'CAMERA' | 'IMAGE'

export interface AnalysisRequest {
  url: string
  source: ScanSource
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

export interface OfficialSiteSuggestion {
  name: string
  url: string
  domain: string
  reason: string
  verified: true
}

// 후보가 없거나 의도를 알 수 없어도 오류가 아닌 200 으로 오며, 원래 링크는 계속 차단한다
export type GuidanceStatus = 'MATCHED' | 'NEEDS_CLARIFICATION' | 'NOT_FOUND'

// QR 링크와 사용자 의도를 비교한 판단. 원래 링크를 열어도 된다는 결론은 주지 않는다
export interface IntentAssessment {
  matchesIntent: boolean | null
  explanation: string
  source: 'llm' | 'rules'
}

export interface IntentGuidance {
  analysisId: string
  guidanceStatus: GuidanceStatus
  intentCode: string | null
  serviceKey: string | null
  serviceName: string | null
  confidence: number
  followUpQuestion: string | null
  assessment: IntentAssessment
  suggestions: OfficialSiteSuggestion[]
}

// POST /reports
export type ReportReason = 'SUSPICIOUS_LOGIN' | 'PAYMENT_REQUEST' | 'IMPERSONATION' | 'MALWARE' | 'OTHER'

export interface ReportRequest {
  analysisId: string
  reason: ReportReason
  description?: string
}

export interface ReportCreated {
  reportId: string
  status: 'PENDING' | 'BLOCKED' | 'SAFE'
  createdAt: string
}

// GET /health
export interface HealthStatus {
  status: 'UP' | 'DEGRADED'
  version: string
  timestamp: string
}
