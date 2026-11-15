"""Optional Ollama-compatible local model adapter."""

from __future__ import annotations

import json
import os

from .base import ExplanationInput, ExplanationProvider, ExplanationResult, HttpRequester
from .http import ModelRequestError, post_json
from .validation import ExplanationValidationError, validate_model_output


class LocalModelProvider(ExplanationProvider):
    source = "local_model"

    def __init__(
        self,
        endpoint: str | None = None,
        model: str | None = None,
        timeout: float = 8.0,
        requester: HttpRequester = post_json,
    ) -> None:
        self.endpoint = endpoint or os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2")
        self.timeout = timeout
        self.requester = requester

    def explain(self, case: ExplanationInput) -> ExplanationResult:
        body = json.dumps({
            "model": self.model,
            "stream": False,
            "format": "json",
            "prompt": f"{_system_prompt()}\nInput:\n{json.dumps(case.as_dict())}",
        }).encode("utf-8")
        try:
            status, raw = self.requester(self.endpoint, {"Content-Type": "application/json"}, body, self.timeout)
            if status != 200:
                return unavailable(case, f"Local model returned HTTP {status}.")
            document = json.loads(raw.decode("utf-8"))
            content = document["response"]
            payload = json.loads(content) if isinstance(content, str) else content
            return validate_model_output(payload, case, self.source)
        except (ModelRequestError, ExplanationValidationError, KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            return unavailable(case, "Local model response was unavailable or invalid.", type(exc).__name__)


def _system_prompt() -> str:
    return (
        "Explain only the supplied application findings. Return JSON with exactly "
        "summary, explanation, recommendations. Never invent evidence, change score "
        "or severity, claim identity/location, or open URLs/files."
    )


def unavailable(case: ExplanationInput, message: str, error: str = "unavailable") -> ExplanationResult:
    return ExplanationResult("local_model", "unavailable", "", "", [], case.risk_score, case.severity, f"{error}: {message}")
