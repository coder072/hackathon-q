import re

# INT-005: 비밀번호·인증번호·계좌번호·주민등록번호·카드번호로 보이는 값.
# 이런 입력은 LLM 에 보내지 않고 바로 거부한다.
SENSITIVE_PATTERNS = (
    re.compile(r"\b\d{6}-?[1-4]\d{6}\b"),  # 주민등록번호
    re.compile(r"\b(?:\d{4}[- ]?){3}\d{4}\b"),  # 카드번호
    re.compile(r"(?:인증번호|otp)\s*[:=]?\s*\d{4,8}\b", re.IGNORECASE),
    re.compile(r"(?:계좌번호|계좌|account)\s*[:=]?\s*\d[\d-]{7,18}\b", re.IGNORECASE),
    re.compile(r"(?:비밀번호|비번|패스워드|password)\s*(?:은|는|[:=])\s*\S{4,}", re.IGNORECASE),
)


def contains_sensitive_data(message: str) -> bool:
    return any(pattern.search(message) for pattern in SENSITIVE_PATTERNS)
