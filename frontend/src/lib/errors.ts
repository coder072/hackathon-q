import { ApiError, type ErrorCode } from '../api'

// 오류 코드별 사용자 안내 (API 명세 "클라이언트 처리" 열)
const MESSAGES: Partial<Record<ErrorCode, string>> = {
  NETWORK_ERROR: '네트워크에 연결되어 있지 않거나 분석 서버에 접속할 수 없어요. 연결을 확인한 뒤 다시 시도해 주세요.',
  INVALID_URL: 'QR 코드의 주소 형식이 올바르지 않아요. 다시 스캔해 주세요.',
  UNSUPPORTED_SCHEME: '지원하지 않는 형식의 QR 코드예요.',
  URL_TOO_LONG: '주소가 너무 길어 분석할 수 없어요.',
  PRIVATE_NETWORK_TARGET: '내부망 주소로 연결되는 QR이라 분석하지 않고 차단했어요.',
  DNS_RESOLUTION_FAILED: '도메인 주소를 확인할 수 없어요. 잠시 후 다시 시도해 주세요.',
  REDIRECT_LIMIT_EXCEEDED: '여러 주소를 과도하게 거쳐 이동해요. 피싱이 의심되니 열지 마세요.',
  RATE_LIMIT_EXCEEDED: '요청이 너무 많아요. 잠시 후 다시 시도해 주세요.',
  ANALYSIS_FAILED: '분석 중 오류가 발생했어요. 안전 여부를 확인하지 못했으니 링크를 열지 마세요.',
  ANALYSIS_TIMEOUT: '분석 시간이 초과됐어요. 다시 시도해 주세요.',
  ANALYSIS_NOT_FOUND: '분석 결과가 만료됐어요. QR을 다시 스캔해 주세요.',
  INVALID_INTENT_MESSAGE: '접속 목적을 1~300자로 입력해 주세요.',
  INTENT_GUIDANCE_NOT_ALLOWED: '이 분석 결과에서는 접속 목적을 확인할 수 없어요. 원래 링크는 계속 차단됩니다.',
  SENSITIVE_DATA_DETECTED: '민감정보로 보이는 값은 전송하지 않았어요. 해당 내용을 지우고 목적만 입력해 주세요.',
  INTENT_SERVICE_UNAVAILABLE: '목적 분석 서비스를 사용할 수 없어요. 원래 링크는 계속 차단됩니다.',
  INTENT_NOT_UNDERSTOOD: '목적을 이해하지 못했어요. 원래 링크는 계속 차단됩니다.',
  OFFICIAL_SITE_NOT_FOUND: '확인된 공식 사이트가 없어요. QR을 제공한 곳에 직접 확인해 주세요.',
}

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return MESSAGES[err.code] ?? err.message
  return '알 수 없는 오류가 발생했어요. 다시 시도해 주세요.'
}
