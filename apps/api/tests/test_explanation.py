import json

from app.analyzers.types import Evidence, Finding
from app.db.enums import Severity
from app.integrations.explanation.base import ExplanationInput
from app.integrations.explanation.fallback import FallbackExplanationProvider
from app.integrations.explanation.hosted import HostedLLMProvider
from app.integrations.explanation.local import LocalModelProvider
from app.integrations.explanation.http import ModelRequestError
from app.integrations.explanation.service import ExplanationService
from app.risk.engine import RiskEngine


def case_input() -> ExplanationInput:
    finding = Finding(
        rule_id="DOMAIN-001",
        category="DOMAIN",
        title="Domain impersonation",
        description="Controlled finding",
        severity="HIGH",
        score_contribution=20,
        confidence=0.9,
        evidence=[Evidence("domain", "example-login.test", "body", "local_rule")],
    )
    result = RiskEngine().score([finding])
    return ExplanationInput.from_risk_result(result)


def test_fallback_is_useful_and_preserves_authoritative_score():
    result = FallbackExplanationProvider().explain(case_input())

    assert result.status == "fallback"
    assert result.source == "deterministic_fallback"
    assert result.risk_score == 20
    assert result.severity == "LOW"
    assert "Domain impersonation" in result.summary
    assert result.recommendations


def test_hosted_provider_validates_mocked_structured_response():
    def requester(url, headers, body, timeout):
        assert headers["Authorization"] == "Bearer test-key"
        request = json.loads(body)
        assert request["response_format"] == {"type": "json_object"}
        return 200, json.dumps({
            "choices": [{"message": {"content": json.dumps({
                "summary": "The supplied domain finding raises concern.",
                "explanation": "This summary is based only on the supplied deterministic evidence.",
                "recommendations": ["Review the domain and preserve the message."],
            })}}]
        }).encode()

    result = HostedLLMProvider(api_key="test-key", endpoint="https://llm.test/chat", requester=requester).explain(case_input())

    assert result.status == "available"
    assert result.source == "hosted_llm"
    assert result.risk_score == 20
    assert result.severity == "LOW"
    assert result.recommendations == ["Review the domain and preserve the message."]


def test_local_provider_validates_mocked_ollama_response():
    def requester(url, headers, body, timeout):
        request = json.loads(body)
        assert request["stream"] is False
        return 200, json.dumps({"response": {
            "summary": "Local explanation",
            "explanation": "Local model summarized the existing finding.",
            "recommendations": ["Preserve evidence."],
        }}).encode()

    result = LocalModelProvider(requester=requester).explain(case_input())

    assert result.status == "available"
    assert result.source == "local_model"
    assert result.risk_score == 20


def test_invalid_model_output_falls_back_without_changing_score():
    def requester(url, headers, body, timeout):
        return 200, json.dumps({"choices": [{"message": {"content": json.dumps({"summary": "invented score", "risk_score": 100})}}]}).encode()

    service = ExplanationService([
        HostedLLMProvider(api_key="key", endpoint="https://llm.test", requester=requester),
    ])
    result = service.explain(case_input())

    assert result.status == "fallback"
    assert result.source == "deterministic_fallback"
    assert result.risk_score == 20
    assert result.severity == "LOW"


def test_unavailable_provider_uses_fallback():
    result = ExplanationService([HostedLLMProvider()]).explain(case_input())

    assert result.status == "fallback"
    assert result.source == "deterministic_fallback"
    assert result.risk_score == 20


def test_timeout_provider_failure_uses_fallback():
    def requester(url, headers, body, timeout):
        raise ModelRequestError("timeout", "timed out")

    result = ExplanationService([
        HostedLLMProvider(api_key="key", endpoint="https://llm.test", requester=requester),
    ]).explain(case_input())

    assert result.status == "fallback"
    assert result.source == "deterministic_fallback"


def test_service_preserves_case_score_even_if_provider_payload_has_extra_authority_fields():
    def requester(url, headers, body, timeout):
        return 200, json.dumps({"response": {
            "summary": "Valid summary",
            "explanation": "Valid explanation",
            "recommendations": ["Preserve evidence."],
        }}).encode()

    result = ExplanationService([LocalModelProvider(requester=requester)]).explain(case_input())

    assert result.risk_score == 20
    assert result.severity == Severity.LOW.value
