import asyncio

import httpx
import pytest

from app.services.analyses.rdap import BOOTSTRAP_URL, RdapClient

BOOTSTRAP = {"services": [[["com", "net"], ["http://rdap.example/", "https://rdap.example/com/"]]]}


def lookup(domain, client=None):
    return asyncio.run((client or RdapClient(timeout=1)).registered_at(domain))


def rdap_domain(events):
    return {"objectClassName": "domain", "events": events}


@pytest.fixture
def rdap(respx_mock):
    respx_mock.get(BOOTSTRAP_URL).mock(return_value=httpx.Response(200, json=BOOTSTRAP))
    return respx_mock


def test_returns_registration_date(rdap):
    rdap.get("https://rdap.example/com/domain/example.com").mock(
        return_value=httpx.Response(
            200,
            json=rdap_domain(
                [
                    {"eventAction": "expiration", "eventDate": "2030-01-01T00:00:00Z"},
                    {"eventAction": "registration", "eventDate": "1995-08-14T04:00:00Z"},
                ]
            ),
        )
    )
    registered = lookup("example.com")
    assert registered is not None
    assert registered.isoformat() == "1995-08-14T04:00:00+00:00"


def test_bootstrap_is_fetched_once(rdap):
    rdap.get(url__startswith="https://rdap.example/com/domain/").mock(
        return_value=httpx.Response(200, json=rdap_domain([]))
    )
    client = RdapClient(timeout=1)
    assert lookup("a.com", client) is None
    assert lookup("b.net", client) is None
    assert rdap.calls.call_count == 3  # 목록 1회 + 도메인 2회


def test_successful_lookup_is_cached(rdap):
    route = rdap.get("https://rdap.example/com/domain/example.com").mock(
        return_value=httpx.Response(
            200,
            json=rdap_domain(
                [{"eventAction": "registration", "eventDate": "2020-01-01T00:00:00Z"}]
            ),
        )
    )
    client = RdapClient(timeout=1)
    assert lookup("example.com", client) == lookup("example.com", client)
    assert route.call_count == 1


@pytest.mark.parametrize(
    "response",
    [httpx.Response(404), httpx.Response(200, text="not json"), httpx.Response(200, json=[])],
)
def test_bad_response_returns_none(rdap, response):
    rdap.get("https://rdap.example/com/domain/example.com").mock(return_value=response)
    assert lookup("example.com") is None


def test_unsupported_tld_returns_none(rdap):
    assert lookup("example.zz") is None


def test_network_error_returns_none(respx_mock):
    respx_mock.get(BOOTSTRAP_URL).mock(side_effect=httpx.ConnectError("down"))
    assert lookup("example.com") is None
