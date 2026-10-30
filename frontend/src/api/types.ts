// API 명세서 기준 타입 (응답 JSON 은 camelCase)

export type Verdict = 'SAFE' | 'SUSPICIOUS'

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
  | 'INTENT_NOT_UNDERSTOOD'
  | 'OFFICIAL_SITE_NOT_FOUND'
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
  originalUrl: string
  finalUrl: string
  displayDomain: string
  redirectCount: number
  checks: CheckResult[]
  analyzedAt: string
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

export interface IntentGuidance {
  intentCode: string
  serviceName: string
  confidence: number
  questionRequired: boolean
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
