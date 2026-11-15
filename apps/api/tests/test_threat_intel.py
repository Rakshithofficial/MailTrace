import json

from app.integrations.threat_intel.base import IndicatorLookup
from app.integrations.threat_intel.local import LocalProvider, NoOpProvider
from app.integrations.threat_intel.service import ThreatIntelService
from app.integrations.threat_intel.urlscan import UrlscanProvider
from app.integrations.threat_intel.virustotal import VirusTotalProvider
from app.integrations.threat_intel.http import ProviderRequestError


def test_local_provider_is_available_without_network():
    indicator = IndicatorLookup("DOMAIN", "example.test")
    provider = LocalProvider({("DOMAIN", "example.test"): {"verdict": "known_benign"}})

    result = provider.lookup(indicator)

    assert result.source == "local"
    assert result.status == "available"
    assert result.result == {"verdict": "known_benign"}


def test_noop_provider_returns_unavailable():
    result = NoOpProvider().lookup(IndicatorLookup("URL", "https://example.test"))

    assert result.status == "unavailable"
    assert "configured" in (result.error or "")


def test_virustotal_normalizes_mocked_response_without_exposing_key():
    def requester(url, headers, timeout):
        assert url.endswith("/domains/example.test")
        assert headers["x-apikey"] == "mock-key"
        assert timeout == 2.0
        return 200, json.dumps({"data": {"attributes": {"reputation": 4, "last_analysis_stats": {"malicious": 0, "suspicious": 1}}}}).encode()

    result = VirusTotalProvider(api_key="mock-key", timeout=2.0, requester=requester).lookup(
        IndicatorLookup("DOMAIN", "example.test")
    )

    assert result.status == "available"
    assert result.source == "virustotal"
    assert result.result == {"reputation": 4, "malicious": 0, "suspicious": 1, "source": "virustotal"}
    assert "mock-key" not in str(result.as_dict())


def test_urlscan_normalizes_mocked_response():
    def requester(url, headers, timeout):
        assert "page.url:https%3A%2F%2Fexample.test%2Flogin" in url
        return 200, json.dumps({"results": [{"task": {"url": "https://example.test/login"}}]}).encode()

    result = UrlscanProvider(api_key="mock-key", requester=requester).lookup(
        IndicatorLookup("URL", "https://example.test/login")
    )

    assert result.status == "available"
    assert result.result["matches"] == 1
    assert result.result["source"] == "urlscan"


def test_external_provider_without_key_returns_unavailable(monkeypatch):
    monkeypatch.delenv("VIRUSTOTAL_API_KEY", raising=False)
    monkeypatch.delenv("URLSCAN_API_KEY", raising=False)

    vt = VirusTotalProvider().lookup(IndicatorLookup("HASH", "a" * 64))
    urlscan = UrlscanProvider().lookup(IndicatorLookup("URL", "https://example.test"))

    assert vt.status == "unavailable"
    assert urlscan.status == "unavailable"


def test_rate_limit_and_timeout_become_unavailable():
    def rate_limited(url, headers, timeout):
        raise ProviderRequestError("rate_limited", "rate limit reached")

    def timed_out(url, headers, timeout):
        raise ProviderRequestError("timeout", "timed out")

    rate_result = VirusTotalProvider(api_key="mock", requester=rate_limited).lookup(IndicatorLookup("IP", "198.51.100.10"))
    timeout_result = UrlscanProvider(api_key="mock", requester=timed_out).lookup(IndicatorLookup("URL", "https://example.test"))

    assert rate_result.status == "unavailable"
    assert timeout_result.status == "unavailable"
    assert "rate limit" in (rate_result.error or "")
    assert "timed out" in (timeout_result.error or "")


def test_service_continues_when_external_providers_fail():
    indicator = IndicatorLookup("DOMAIN", "example.test")
    local = LocalProvider({("DOMAIN", "example.test"): {"verdict": "known_benign"}})
    unavailable = NoOpProvider()

    result = ThreatIntelService([local, unavailable]).enrich([indicator])

    assert result.status == "available"
    assert [provider.source for provider in result.providers] == ["local", "noop"]
    assert result.providers[0].result["verdict"] == "known_benign"
    assert all(provider.source != "local" or provider.status == "available" for provider in result.providers)
