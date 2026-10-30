import pytest

from app.core.errors import AppError
from app.services.analyses.parsing import normalize_url
from app.services.analyses.rules import (
    find_lookalike_brand,
    load_catalog,
    registrable_domain,
    structure_issue,
    suspicious_tld,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("HTTPS://WWW.Naver.COM:443", "https://www.naver.com/"),
        ("http://example.com/a b", None),  # 인코딩되지 않은 공백은 잘못된 URL
        ("https://네이버.com/경로", "https://xn--950bt9s8xi.com/%EA%B2%BD%EB%A1%9C"),
        ("http://0x7f.1/", "http://127.0.0.1/"),
        ("https://user:pw@evil.com/", "https://evil.com/"),
        ("https://example.com.:8443/x?q=1", "https://example.com:8443/x?q=1"),
    ],
)
def test_normalize_url(raw, expected):
    if expected is None:
        with pytest.raises(AppError):
            normalize_url(raw)
    else:
        assert normalize_url(raw).url == expected


def test_userinfo_is_flagged():
    assert normalize_url("https://naver.com@evil.com/").has_userinfo


@pytest.mark.parametrize(
    ("host", "brand"),
    [
        ("www.naver.com", None),
        ("nid.naver.com", None),
        ("naver-login.xyz", "naver"),
        ("nav3r.com", "naver"),
        ("kakaq.com", "kakao"),
        ("rnicrosoft-support.com", "microsoft"),
        ("naver.com.secure-check.top", "naver"),
        ("example.com", None),
        ("8.8.8.8", None),
    ],
)
def test_lookalike(host, brand):
    assert find_lookalike_brand(host, load_catalog()) == brand


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("a.b.example.com", "example.com"),
        ("www.epost.go.kr", "epost.go.kr"),
        ("1.2.3.4", "1.2.3.4"),
    ],
)
def test_registrable_domain(host, expected):
    assert registrable_domain(host) == expected


@pytest.mark.parametrize(
    ("url", "flagged"),
    [
        ("https://www.naver.com/login/verify", False),  # 공식 도메인은 키워드 검사 제외
        ("https://shop.example.com/login/verify", True),
        ("https://a.b.c.example.com/", True),
        ("https://xn--950bt9s8xi.com/", True),
        ("https://example.com/" + "a" * 200, True),
        ("https://example.com/products", False),
    ],
)
def test_structure_issue(url, flagged):
    assert (structure_issue([normalize_url(url)], load_catalog()) is not None) is flagged


@pytest.mark.parametrize(
    ("host", "tld"),
    [
        ("event-gift.shop", "shop"),
        ("a.b.example.xyz", "xyz"),
        ("example.com", None),
        ("www.epost.go.kr", None),
        ("1.2.3.4", None),
    ],
)
def test_suspicious_tld(host, tld):
    assert suspicious_tld(host, load_catalog()) == tld
