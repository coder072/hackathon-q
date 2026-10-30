from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_URL = "INVALID_URL"
    UNSUPPORTED_SCHEME = "UNSUPPORTED_SCHEME"
    URL_TOO_LONG = "URL_TOO_LONG"
    PRIVATE_NETWORK_TARGET = "PRIVATE_NETWORK_TARGET"
    DNS_RESOLUTION_FAILED = "DNS_RESOLUTION_FAILED"
    REDIRECT_LIMIT_EXCEEDED = "REDIRECT_LIMIT_EXCEEDED"
    ANALYSIS_TIMEOUT = "ANALYSIS_TIMEOUT"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    ANALYSIS_NOT_FOUND = "ANALYSIS_NOT_FOUND"
    REPORT_ALREADY_EXISTS = "REPORT_ALREADY_EXISTS"
    INVALID_REPORT_REASON = "INVALID_REPORT_REASON"
    INVALID_INTENT_MESSAGE = "INVALID_INTENT_MESSAGE"
    INTENT_GUIDANCE_NOT_ALLOWED = "INTENT_GUIDANCE_NOT_ALLOWED"
    SENSITIVE_DATA_DETECTED = "SENSITIVE_DATA_DETECTED"
    INTENT_SERVICE_UNAVAILABLE = "INTENT_SERVICE_UNAVAILABLE"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"


# API 명세 5. 오류 코드
ERROR_SPECS: dict[ErrorCode, tuple[int, str]] = {
    ErrorCode.INVALID_REQUEST: (400, "요청 형식이 올바르지 않습니다."),
    ErrorCode.INVALID_URL: (400, "분석할 수 없는 URL입니다."),
    ErrorCode.UNSUPPORTED_SCHEME: (400, "HTTP 또는 HTTPS URL만 분석할 수 있습니다."),
    ErrorCode.URL_TOO_LONG: (400, "URL 길이 제한을 초과했습니다."),
    ErrorCode.PRIVATE_NETWORK_TARGET: (400, "내부망 또는 로컬 주소는 분석할 수 없습니다."),
    ErrorCode.DNS_RESOLUTION_FAILED: (422, "도메인 주소를 확인할 수 없습니다."),
    ErrorCode.REDIRECT_LIMIT_EXCEEDED: (422, "리디렉션 허용 횟수를 초과했습니다."),
    ErrorCode.ANALYSIS_TIMEOUT: (504, "분석 제한 시간을 초과했습니다."),
    ErrorCode.ANALYSIS_FAILED: (500, "분석 처리 중 오류가 발생했습니다."),
    ErrorCode.ANALYSIS_NOT_FOUND: (404, "분석 결과가 없거나 보관 기간이 만료되었습니다."),
    ErrorCode.REPORT_ALREADY_EXISTS: (409, "이미 신고된 분석 결과입니다."),
    ErrorCode.INVALID_REPORT_REASON: (422, "지원하지 않는 신고 사유입니다."),
    ErrorCode.INVALID_INTENT_MESSAGE: (400, "접속 목적을 1~300자로 입력해 주세요."),
    ErrorCode.INTENT_GUIDANCE_NOT_ALLOWED: (409, "접속 의도 확인 대상이 아닙니다."),
    ErrorCode.SENSITIVE_DATA_DETECTED: (422, "민감정보로 보이는 값을 제거해 주세요."),
    ErrorCode.INTENT_SERVICE_UNAVAILABLE: (503, "접속 의도 분석 서비스를 사용할 수 없습니다."),
    ErrorCode.RATE_LIMIT_EXCEEDED: (429, "요청 횟수 제한을 초과했습니다."),
    ErrorCode.UNAUTHORIZED: (401, "인증에 실패했습니다."),
    ErrorCode.FORBIDDEN: (403, "권한이 없습니다."),
}


class AppError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str | None = None,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        self.code = code
        self.status_code, default_message = ERROR_SPECS[code]
        self.message = message or default_message
        self.details = details or []
        super().__init__(self.message)
