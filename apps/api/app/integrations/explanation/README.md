# Optional LLM Explanation Layer

The explanation layer is not a detector. It receives only structured findings and the already-calculated risk score/severity from the application.

## Providers

- `HostedLLMProvider`: optional OpenAI-compatible JSON chat endpoint.
- `LocalModelProvider`: optional Ollama-compatible `/api/generate` endpoint.
- `FallbackExplanationProvider`: deterministic explanation that requires no model or network.

## Configuration

- `LLM_API_KEY` and `LLM_API_URL` enable the hosted adapter.
- `LLM_MODEL` optionally selects the hosted model.
- `OLLAMA_URL` and `OLLAMA_MODEL` optionally configure the local adapter.

No credentials are hard-coded. The fallback is used when configuration is missing, a provider times out, is unavailable, is rate-limited, returns malformed JSON, or violates the output schema.

## Output contract

Models must return exactly:

```json
{
  "summary": "Plain-language summary grounded in supplied findings.",
  "explanation": "Explanation of the supplied evidence.",
  "recommendations": ["Defensive action grounded in supplied evidence."]
}
```

Models cannot return or change `risk_score`, `severity`, findings, evidence, attacker identity, or physical location. They must not execute or open URLs/files. The service preserves application-owned score and severity fields even after a valid model response.