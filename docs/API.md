# MailTrace API Contract

**Status:** Planning contract for the MVP  
**Style:** REST/JSON over HTTP under `/api/v1`  
**Authentication:** Deferred for the student MVP; deployment authentication is an unresolved decision.

## 1. API Structure

The FastAPI backend is a modular monolith. Routes are grouped by resource:

- `/cases` - investigation lifecycle and case summaries
- `/cases/{case_id}/email` - parsed email and extracted evidence
- `/cases/{case_id}/analysis` - deterministic analysis and optional enrichment/AI explanation
- `/cases/{case_id}/findings` - evidence-backed findings
- `/cases/{case_id}/relationships` - related indicators and possible campaigns
- `/cases/{case_id}/report` - report generation and retrieval
- `/indicators` - normalized indicator lookup
- `/health` - service readiness and dependency status

All timestamps use ISO 8601 UTC. IDs are opaque strings, preferably UUIDs. JSON field names use `snake_case`.

## 2. Endpoint Names

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Return API and dependency health without exposing secrets. |
| `POST` | `/cases` | Create a case from an `.eml` upload or pasted content. |
| `GET` | `/cases` | List cases with filters for status, severity, and date. |
| `GET` | `/cases/{case_id}` | Return the case overview. |
| `PATCH` | `/cases/{case_id}` | Update allowed workflow fields such as status or analyst notes. |
| `POST` | `/cases/{case_id}/analyze` | Run local analysis and optional configured enrichment. Safe to repeat. |
| `GET` | `/cases/{case_id}/email` | Return parsed email metadata, headers, body preview, URLs, and attachments. |
| `GET` | `/cases/{case_id}/analysis` | Return the latest analysis result. |
| `GET` | `/cases/{case_id}/findings` | List findings with evidence and score contributions. |
| `GET` | `/cases/{case_id}/relationships` | Return related indicators, cases, and campaign context. |
| `POST` | `/cases/{case_id}/explanation` | Request an LLM/local-model explanation, with template fallback. |
| `POST` | `/cases/{case_id}/report` | Generate a report from stored case data. |
| `GET` | `/cases/{case_id}/report` | Retrieve the latest report or report metadata. |
| `GET` | `/indicators/{indicator_id}` | Return an indicator and its observed relationships. |

The API must never automatically fetch or open a suspicious URL. URL enrichment, when enabled, uses a controlled server-side provider adapter and must be explicitly configured.

## 3. Intake Request Schema

`POST /cases` accepts `multipart/form-data` with exactly one primary input:

```json
{
  "title": "Invoice review",
  "source_type": "eml",
  "raw_email": "<optional pasted RFC 5322 content>",
  "analyst_note": "<optional string>"
}
```

An uploaded `.eml` file is preferred. The server stores a reference and a SHA-256 hash; it does not execute attachments or macros. `source_type` is `eml` or `pasted`.

## 4. Common Response Schemas

### Case

```json
{
  "id": "case-uuid",
  "title": "Invoice review",
  "status": "ANALYZING",
  "risk_score": 68,
  "severity": "HIGH",
  "verdict": "SUSPICIOUS",
  "summary": "Evidence-backed summary or fallback text.",
  "created_at": "2026-09-23T10:00:00Z",
  "updated_at": "2026-09-23T10:02:00Z"
}
```

Allowed statuses: `RECEIVED`, `PARSING`, `ANALYZING`, `REVIEW`, `CLOSED`, `FAILED`. Allowed verdicts: `BENIGN`, `SUSPICIOUS`, `MALICIOUS`, `INCONCLUSIVE`.

### Analysis Result

```json
{
  "case_id": "case-uuid",
  "analyzer_version": "rules-1",
  "completed_at": "2026-09-23T10:02:00Z",
  "findings": [],
  "indicators": [],
  "relationships": [],
  "infrastructure": {
    "source_ips": [],
    "dns_context": [],
    "asn_isp": [],
    "approximate_geolocation": [],
    "limitations": "Context is approximate and depends on available local or optional enrichment data."
  },
  "risk": {
    "score": 68,
    "severity": "HIGH",
    "contributors": [
      {"rule_id": "URL-002", "label": "Look-alike domain", "contribution": 20, "evidence_ids": ["evidence-1"]}
    ]
  },
  "enrichment": {"status": "SKIPPED", "providers": []},
  "explanation": {
    "status": "FALLBACK",
    "source": "deterministic_fallback",
    "summary": "Generated from deterministic findings.",
    "text": "Generated from deterministic findings.",
    "recommendations": ["Preserve evidence and review the cited findings."],
    "risk_score": 68,
    "severity": "HIGH"
  }
}
```

Explanation output is a supporting layer. The application-owned risk score, severity, findings, and evidence remain authoritative and cannot be changed by a model. A missing or failed model returns deterministic fallback text.

### Finding

```json
{
  "id": "finding-uuid",
  "case_id": "case-uuid",
  "category": "URL",
  "rule_id": "URL-002",
  "title": "Look-alike domain",
  "description": "The visible brand and registered domain do not match.",
  "severity": "HIGH",
  "score_contribution": 20,
  "evidence": [{"type": "url", "value": "https://example-login.test", "location": "body"}],
  "confidence": 0.9
}
```

### Indicator

```json
{
  "id": "indicator-uuid",
  "type": "DOMAIN",
  "value": "Example-Login.TEST",
  "normalized_value": "example-login.test",
  "source": "email_body",
  "confidence": 0.95,
  "first_seen": "2026-09-23T10:00:00Z",
  "last_seen": "2026-09-23T10:00:00Z"
}
```

Types: `IP`, `DOMAIN`, `URL`, `HASH`, `EMAIL`, `ASN`.

### Relationship

```json
{
  "id": "relationship-uuid",
  "source_indicator_id": "indicator-uuid-1",
  "target_indicator_id": "indicator-uuid-2",
  "source_case_id": "case-uuid-a",
  "target_case_id": "case-uuid-b",
  "relationship_type": "OBSERVED_DOMAIN",
  "confidence": 1.0,
  "strength": "STRONG",
  "evidence": ["same normalized domain"]
}
```

### Report

```json
{
  "id": "report-uuid",
  "case_id": "case-uuid",
  "format": "json",
  "generated_at": "2026-09-23T10:05:00Z",
  "sections": ["overview", "email", "findings", "relationships", "recommendations", "limitations"],
  "content_reference": "reports/case-uuid.json"
}
```

## 5. Error Response Format

All handled errors use the same shape and an appropriate HTTP status:

```json
{
  "error": {
    "code": "CASE_NOT_FOUND",
    "message": "The requested case does not exist.",
    "details": [{"field": "case_id", "issue": "unknown id"}],
    "request_id": "request-uuid"
  }
}
```

Do not return raw stack traces, API keys, or full uploaded email contents in errors. Typical codes include `INVALID_INPUT`, `UNSUPPORTED_FILE`, `PAYLOAD_TOO_LARGE`, `CASE_NOT_FOUND`, `ANALYSIS_FAILED`, `DEPENDENCY_UNAVAILABLE`, and `INTERNAL_ERROR`.

## 6. Investigation Case Lifecycle

`RECEIVED -> PARSING -> ANALYZING -> REVIEW -> CLOSED`.

A parse or analysis failure moves the case to `FAILED` with a safe error record. A failed case can be retried by an explicit analyze operation. `REVIEW` means results are available for analyst confirmation; `CLOSED` means the analyst has completed the investigation. Re-running analysis creates a new analysis result version rather than silently deleting prior evidence.

## 7. Contract Rules

- Deterministic findings and their evidence remain authoritative for risk scoring.
- LLM output is labeled as explanation/supporting text and may be unavailable.
- Optional threat-intelligence providers are adapters; provider failure returns partial results and does not fail the case.
- Approximate infrastructure context must be labeled approximate. The API must not claim exact identity or physical location.
- Response recommendations include action, reason, priority, and evidence references.
