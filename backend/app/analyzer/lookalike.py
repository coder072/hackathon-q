"""URL-005 유사 도메인 탐지."""

import tldextract

# 네트워크 없이 내장 Public Suffix List 스냅샷만 사용
_extract = tldextract.TLDExtract(suffix_list_urls=())

# 브랜드 키워드 → 공식 등록 도메인
BRANDS: dict[str, set[str]] = {
    "naver": {"naver.com", "naver.me"},
    "kakao": {"kakao.com", "kakaocorp.com", "daum.net"},
    "google": {"google.com", "google.co.kr", "goo.gl", "youtube.com"},
    "apple": {"apple.com", "icloud.com"},
    "microsoft": {"microsoft.com", "live.com", "office.com"},
    "paypal": {"paypal.com"},
    "coupang": {"coupang.com"},
    "toss": {"toss.im", "tossbank.com"},
    "samsung": {"samsung.com"},
    "shinhan": {"shinhan.com", "shinhancard.com"},
    "kbstar": {"kbstar.com", "kbcard.com"},
    "wooribank": {"wooribank.com"},
    "hanabank": {"hanabank.com"},
    "nhbank": {"nonghyup.com", "nhbank.com"},
    "epost": {"epost.go.kr"},
    "cjlogistics": {"cjlogistics.com"},
    "instagram": {"instagram.com"},
    "facebook": {"facebook.com"},
    "amazon": {"amazon.com"},
}

# 숫자·문자 치환 정규화
HOMOGLYPHS = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a"})


def registrable_domain(host: str) -> str:
    ext = _extract(host)
    return ext.top_domain_under_public_suffix or host


def _levenshtein(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def find_impersonated_brand(host: str) -> str | None:
    """공식 도메인이 아닌데 브랜드 이름(또는 변형)을 포함하면 해당 브랜드를 반환한다."""
    reg = registrable_domain(host)
    if any(reg in official for official in BRANDS.values()):
        return None

    ext = _extract(host)
    labels = [p for p in (ext.subdomain.split(".") + [ext.domain]) if p]
    normalized = [lbl.translate(HOMOGLYPHS).replace("rn", "m") for lbl in labels]

    for brand in BRANDS:
        for lbl in normalized:
            tokens = lbl.split("-")
            # 접두·접미어 조합 (naver-login), 철자 변형 (navver, naverr)
            if brand in lbl or any(len(brand) >= 5 and _levenshtein(t, brand) <= 1 for t in tokens):
                return brand
    return None
