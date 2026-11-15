"""Read-only urlscan.io URL search adapter."""

from __future__ import annotations

import json
import os
from urllib.parse import quote

from .base import HttpRequester, IndicatorLookup, ProviderResult, ThreatIntelProvider
from .http import ProviderRequestError, request_json


class UrlscanProvider(ThreatIntelProvider):
    source = "urlscan"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://urlscan.io/api/v1/search/",
        timeout: float = 5.0,
        requester: HttpRequester = request_json,
    ) -> None:
        self.api_key = api_key or os.getenv("URLSCAN_API_KEY")
        self.base_url = base_url
        self.timeout = timeout
        self.requester = requester

    def lookup(self, indicator: IndicatorLookup) -> ProviderResult:
        if not self.api_key:
            return _unavailable(indicator, "URLSCAN_API_KEY is not configured.")
        if indicator.indicator_type.upper() != "URL":
            return _unavailable(indicator, "Indicator type is not supported by urlscan adapter.")

        endpoint = f"{self.base_url}?q=page.url:{quote(indicator.normalized_value, safe='')}"
        try:
            response_status, payload = self.requester(
                endpoint,
                {"api-key": self.api_key, "accept": "application/json"},
                self.timeout,
            )
            if response_status == 429:
                return _unavailable(indicator, "urlscan rate limit reached.", "rate_limited")
            if response_status != 200:
                return _unavailable(indicator, f"urlscan returned HTTP {response_status}.")
            document = json.loads(payload.decode("utf-8"))
            results = document.get("results", [])
            return ProviderResult(
                source=self.source,
                indicator_type=indicator.indicator_type,
                normalized_value=indicator.normalized_value,
                status="available",
                result={"matches": len(results), "results": results[:10], "source": self.source},
            )
        except ProviderRequestError as exc:
            return _unavailable(indicator, str(exc), exc.kind)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, AttributeError) as exc:
            return _unavailable(indicator, "urlscan returned an invalid response.", type(exc).__name__)


def _unavailable(indicator: IndicatorLookup, message: str, error: str = "unavailable") -> ProviderResult:
    return ProviderResult("urlscan", indicator.indicator_type, indicator.normalized_value, "unavailable", error=message)
