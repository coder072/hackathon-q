import pytest

from app.analyzer.lookalike import find_impersonated_brand
from app.analyzer.normalizer import normalize_url
from app.analyzer.scoring import decide
from app.core.errors import AppError, ErrorCode
from app.schemas.analysis import CheckResult, Verdict


def test_normalize_lowercases_host_and_drops_default_port():
    n = normalize_url("HTTPS://Example.COM:443/a b", 2048)
    assert n.url == "https://example.com/a%20b"
    assert n.host == "example.com"


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        ("ftp://example.com", ErrorCode.UNSUPPORTED_SCHEME),
        ("https://user:pw@example.com", ErrorCode.INVALID_URL),
        ("not a url", ErrorCode.INVALID_URL),
        ("https://example.com/" + "a" * 3000, ErrorCode.URL_TOO_LONG),
    ],
)
def test_normalize_rejects(raw, code):
    with pytest.raises(AppError) as e:
        normalize_url(raw, 2048)
    assert e.value.code == code


@pytest.mark.parametrize(
    ("host", "brand"),
    [
        ("naver-login.example", "naver"),
        ("nav3r.com", "naver"),
        ("paypa1-secure.com", "paypal"),
        ("www.naver.com", None),
        ("example.com", None),
    ],
)
def test_lookalike(host, brand):
    assert find_impersonated_brand(host) == brand


def _ck(code, score):
    return CheckResult(code=code, detected=True, score=score, message="")


def test_decide_thresholds():
    assert decide([_ck("HTTPS_NOT_USED", 1)]) == (1, Verdict.SAFE)
    assert decide([_ck("HTTPS_NOT_USED", 1), _ck("DIRECT_IP_ACCESS", 3)]) == (4, Verdict.SUSPICIOUS)
    assert decide([_ck("BLOCKLIST_MATCH", 10), _ck("HTTPS_NOT_USED", 1)]) == (
        10,
        Verdict.SUSPICIOUS,
    )
