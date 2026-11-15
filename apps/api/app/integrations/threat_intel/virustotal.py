"""Read-only VirusTotal indicator lookup adapter."""

from __future__ import annotations

import base64
import json
import os
from urllib.parse import quote

from .base import HttpRequester, IndicatorLookup, ProviderResult, ThreatIntelProvider
from .http import ProviderRequestError, request_json


class VirusTotalProvider(ThreatIntelProvider):
    source = "virustotal"
    supported_types = {"IP", "DOMAIN", "URL", "HASH"}

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://www.virustotal.com/api/v3",
        timeout: float = 5.0,
        requester: HttpRequester = request_json,
    ) -> None:
        self.api_key = api_key or os.getenv("VIRUSTOTAL_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.requester = requester

    def lookup(self, indicator: IndicatorLookup) -> ProviderResult:
        indicator_type = indicator.indicator_type.upper()
        if not self.api_key:
            return _unavailable(indicator, "VIRUSTOTAL_API_KEY is not configured.")
        if indicator_type not in self.supported_types:
            return _unavailable(indicator, "Indicator type is not supported by VirusTotal adapter.")

        # VirusTotal uses different resource names for each indicator type.
        resource_paths = {
            "IP": "ip_addresses",
            "DOMAIN": "domains",
            "URL": "urls",
            "HASH": "files",
        }
        if indicator_type == "URL":
            # The URL resource identifier is URL-safe base64 without padding.
            resource_id = (
                base64.urlsafe_b64encode(indicator.normalized_value.encode("utf-8"))
                .decode("ascii")
                .rstrip("=")
            )
        else:
            resource_id = quote(indicator.normalized_value, safe="")

        endpoint = f"{self.base_url}/{resource_paths[indicator_type]}/{resource_id}"
        try:
            response_status, payload = self.requester(
                endpoint,
                {"x-apikey": self.api_key, "accept": "application/json"},
                self.timeout,
            )
            if response_status == 429:
                return _unavailable(indicator, "VirusTotal rate limit reached.", "rate_limited")
            if response_status != 200:
                return _unavailable(indicator, f"VirusTotal returned HTTP {response_status}.")
            document = json.loads(payload.decode("utf-8"))
            attributes = document.get("data", {}).get("attributes", {})
            return ProviderResult(
                source=self.source,
                indicator_type=indicator.indicator_type,
                normalized_value=indicator.normalized_value,
                status="available",
                result={
                    "reputation": attributes.get("reputation"),
                    "malicious": attributes.get("last_analysis_stats", {}).get("malicious", 0),
                    "suspicious": attributes.get("last_analysis_stats", {}).get("suspicious", 0),
                    "source": self.source,
                },
            )
        except ProviderRequestError as exc:
            return _unavailable(indicator, str(exc), exc.kind)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, AttributeError) as exc:
            return _unavailable(indicator, "VirusTotal returned an invalid response.", type(exc).__name__)


def _unavailable(indicator: IndicatorLookup, message: str, error: str = "unavailable") -> ProviderResult:
    return ProviderResult(
        "virustotal",
        indicator.indicator_type,
        indicator.normalized_value,
        "unavailable",
        error=message,
    )
