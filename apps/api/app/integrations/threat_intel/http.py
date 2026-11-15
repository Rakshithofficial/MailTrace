"""Small read-only HTTP helper with bounded timeout and response size."""

from __future__ import annotations

from collections.abc import Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class ProviderRequestError(RuntimeError):
    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind


def request_json(url: str, headers: Mapping[str, str], timeout: float) -> tuple[int, bytes]:
    request = Request(url, headers=dict(headers), method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read(MAX_RESPONSE_BYTES + 1)
            if len(payload) > MAX_RESPONSE_BYTES:
                raise ProviderRequestError("response_too_large", "Provider response exceeded the safe size limit.")
            return response.status, payload
    except HTTPError as exc:
        if exc.code == 429:
            raise ProviderRequestError("rate_limited", "Provider rate limit reached.") from exc
        raise ProviderRequestError("http_error", f"Provider returned HTTP {exc.code}.") from exc
    except TimeoutError as exc:
        raise ProviderRequestError("timeout", "Provider request timed out.") from exc
    except URLError as exc:
        raise ProviderRequestError("unavailable", "Provider could not be reached.") from exc
