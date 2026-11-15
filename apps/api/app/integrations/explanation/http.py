"""Bounded JSON POST helper for optional model providers."""

from __future__ import annotations

from collections.abc import Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MAX_RESPONSE_BYTES = 512 * 1024


class ModelRequestError(RuntimeError):
    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind


def post_json(url: str, headers: Mapping[str, str], body: bytes, timeout: float) -> tuple[int, bytes]:
    request = Request(url, data=body, headers=dict(headers), method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read(MAX_RESPONSE_BYTES + 1)
            if len(payload) > MAX_RESPONSE_BYTES:
                raise ModelRequestError("response_too_large", "Model response exceeded the safe size limit.")
            return response.status, payload
    except HTTPError as exc:
        if exc.code == 429:
            raise ModelRequestError("rate_limited", "Model rate limit reached.") from exc
        raise ModelRequestError("http_error", f"Model returned HTTP {exc.code}.") from exc
    except TimeoutError as exc:
        raise ModelRequestError("timeout", "Model request timed out.") from exc
    except URLError as exc:
        raise ModelRequestError("unavailable", "Model could not be reached.") from exc
