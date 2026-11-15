# MailTrace Threat Rules

**Purpose:** Define explainable, deterministic MVP checks. Rules create evidence-backed findings; the LLM may explain them but cannot replace them.

## 1. Rule Output Contract

Each triggered rule emits:

```json
{
  "rule_id": "AUTH-001",
  "category": "AUTHENTICATION",
  "title": "SPF failed",
  "severity": "HIGH",
  "score_contribution": 15,
  "confidence": 0.9,
  "evidence": [{"type": "header", "name": "Authentication-Results", "value": "spf=fail"}],
  "limitations": "Authentication results are trusted only as parsed header evidence."
}
```

Rules must be safe to run on untrusted text. Do not execute attachments, macros, embedded scripts, or URLs.

## 2. Sender Checks

| Rule | Check | Default contribution |
|---|---|---:|
| `SENDER-001` | From address is malformed or missing. | 10 |
| `SENDER-002` | Display name and address domain are inconsistent with the visible organization. | 10 |
| `SENDER-003` | Reply-To domain differs from From domain without an explainable reason. | 10 |
| `SENDER-004` | Sender domain is a look-alike of a configured/reference brand. | 15 |

Evidence includes the original and normalized addresses, not a claimed identity conclusion.

## 3. Header Checks

| Rule | Check | Default contribution |
|---|---|---:|
| `HEADER-001` | Missing or malformed `Date`, `From`, or `Message-ID`. | 5 |
| `HEADER-002` | Suspicious Received-chain inconsistency or malformed hop. | 10 |
| `HEADER-003` | Trace header contains private/test values or unusual ordering. | 5 |
| `HEADER-004` | Header disagreement between visible sender and routing evidence. | 10 |

Header checks report inconsistencies and observed hops. They do not prove origin or attacker identity.

## 4. Authentication-Result Checks

Parse `Authentication-Results`, `Received-SPF`, and supported DKIM/DMARC indicators as evidence.

| Rule | Check | Default contribution |
|---|---|---:|
| `AUTH-001` | SPF result is `fail` or `softfail`. | 15 |
| `AUTH-002` | DKIM result is `fail` or missing where expected. | 10 |
| `AUTH-003` | DMARC result is `fail`. | 15 |
| `AUTH-004` | Authentication results disagree across headers. | 10 |

A missing result is not automatically malicious; confidence and explanation must reflect missing context.

## 5. URL Checks

Extract URLs without requesting them. Parse them with a mature URL parser and retain the surrounding text location.

| Rule | Check | Default contribution |
|---|---|---:|
| `URL-001` | Obfuscated URL, encoded host, userinfo, or excessive redirects implied by text. | 15 |
| `URL-002` | Visible brand/link text does not match the normalized registered domain. | 20 |
| `URL-003` | Raw IP host, punycode, unusual port, or suspicious top-level domain. | 10 |
| `URL-004` | Local/static reputation provider reports a malicious URL. | 25 |
| `URL-005` | URL shortener is present. | 10 |

External URL providers are optional enrichment. A provider failure produces a dependency note, not a malicious finding.

## 6. Domain Checks

- Normalize lower-case hostnames, remove a terminal dot, and compare effective domains using a maintained public-suffix-aware library.
- Flag `DOMAIN-001` for brand look-alike/typosquatting signals such as edit distance, homoglyphs, or suspicious substitutions: 20.
- Flag `DOMAIN-002` for newly observed or uncommon domain only when reliable local/enrichment data exists: 10.
- Flag `DOMAIN-003` for mismatched link, sender, and reply-to domains: 10.
- Never infer maliciousness from a country-code top-level domain alone.

## 7. Attachment Checks

Treat all uploaded attachments as inert bytes or metadata.

| Rule | Check | Default contribution |
|---|---|---:|
| `ATTACH-001` | Double extension, misleading filename, or mismatch between name and MIME type. | 10 |
| `ATTACH-002` | High-risk type such as executable, script, macro-enabled document, archive, or disk image. | 15 |
| `ATTACH-003` | Archive contains suspicious names/metadata when safely inspected without execution. | 15 |
| `ATTACH-004` | Attachment hash matches a configured threat-intelligence hit. | 20 |

Calculate SHA-256 hashes. Do not open, render, mount, macro-scan by execution, or launch attachments.

## 8. Social-Engineering and Content Checks

Use transparent pattern matching and optional supporting classifiers.

| Rule | Check | Default contribution |
|---|---|---:|
| `CONTENT-001` | Urgency, threat, payment, credential, or account-lock language. | 10 |
| `CONTENT-002` | Request for secrets, payment, gift cards, or unusual transfer. | 15 |
| `CONTENT-003` | Brand impersonation or authority claim supported by content evidence. | 10 |
| `CONTENT-004` | QR code or image-only call to action, where safe static extraction is supported. | 10 |
| `CONTENT-005` | Obfuscated or hidden text signals. | 10 |

Content signals are supporting evidence and must not alone establish a malicious verdict.

## 9. Evidence Format

Every finding must include a stable rule ID, category, title, description, severity, contribution, confidence, and one or more evidence records. Evidence records contain:

- `type`: `header`, `address`, `url`, `domain`, `attachment`, `body_text`, `ip`, `external_result`
- `value`: redacted or normalized value where possible
- `location`: header name, body character range, attachment filename, or parser path
- `source`: local parser, deterministic rule, or named provider
- `observed_at`: timestamp
- `limitations`: what the evidence cannot prove

Avoid logging full sensitive bodies or secrets. Evidence must be reproducible from the stored case input and analyzer version.

## 10. Risk-Score Contributions and Severity

Start with the blueprint weights: sender anomaly +15, domain impersonation +20, malicious URL +25, header/auth anomaly +15, suspicious attachment +10, social engineering +10, and threat-intelligence hit +20. Individual rules use the defaults above, while duplicate evidence is de-duplicated by rule/category before scoring.

The risk engine sums capped contributions and normalizes to 0-100. It records each contributor and evidence ID. A provider hit may contribute only once per indicator category even if several providers agree.

- `0-24`: LOW
- `25-49`: MEDIUM
- `50-74`: HIGH
- `75-100`: CRITICAL

These ranges are initial defaults and must be tuned against fixed synthetic test cases. A high score is a risk assessment, not proof of attacker identity, exact origin, or physical location.
