# MailTrace Sample Data Plan

All development and demonstration messages must be controlled, synthetic, and safe. Use reserved test domains such as `.test`, fake identities, fake IP addresses, and non-routable or inert URLs. Do not include real credentials, personal data, live malware, or links intended to be opened.

## Directory Structure

```text
sample_data/
├── benign/
├── phishing/
├── spoofing/
└── campaign/
```

Each `.eml` fixture should have a nearby metadata file, for example `case.json`, containing:

```json
{
  "sample_id": "phishing-001",
  "category": "phishing",
  "expected_verdict": "SUSPICIOUS",
  "expected_rule_ids": ["URL-002", "CONTENT-001"],
  "shared_indicators": [],
  "notes": "Synthetic training/demo fixture; do not open extracted URLs."
}
```

## Benign Emails

Purpose: provide known-good controls and reduce false positives. Include ordinary synthetic messages with consistent sender domains, normal headers, no risky attachments, and harmless text. Expected outcomes should usually be `BENIGN` or low risk. Include at least one multipart message and one message with a normal document metadata fixture.

## Phishing Emails

Purpose: exercise malicious-element detection and response guidance. Include synthetic credential lures with urgency, a mismatched visible link, a look-alike domain, or a suspicious attachment name. Each fixture must state which rules should trigger and why. URLs remain inert and must never be automatically opened.

## Spoofing Emails

Purpose: exercise sender, header, and authentication checks. Include controlled messages with From/Reply-To mismatch, inconsistent Received headers, and SPF/DKIM/DMARC result examples. These fixtures should demonstrate that authentication evidence is reported without claiming exact origin or attacker identity.

## Related Campaign Emails

Purpose: exercise relationship and possible-campaign logic. Include at least two phishing or spoofing messages that deliberately share one strong indicator, such as a normalized domain, URL, source IP, or attachment SHA-256 hash. They may also share wording or infrastructure as medium/weak evidence. Metadata must identify the intended shared indicator and the expected confidence/strength.

## Fixture Safety and Review

- Store only inert RFC 5322/MIME data and safe metadata.
- Use a reserved `.test` namespace and clearly fake addresses.
- Test parsers and hashes in isolated development environments.
- Keep expected findings versioned when rule behavior changes.
- Review every fixture before a demo and remove accidental real-world indicators.
