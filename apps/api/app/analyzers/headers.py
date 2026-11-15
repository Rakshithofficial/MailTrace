"""Structural header checks without asserting message origin."""

from app.intake.parser import ParsedEmail

from .types import Evidence, Finding


def analyze_headers(email: ParsedEmail) -> list[Finding]:
    findings: list[Finding] = []
    missing = [name for name, value in (("From", email.sender), ("Date", email.sent_at), ("Message-ID", email.message_id)) if not value]
    if missing:
        findings.append(Finding("HEADER-001", "HEADER", "Required headers missing", f"Missing or unparsed headers: {', '.join(missing)}.", "LOW", 5, 0.98, [Evidence("header", ", ".join(missing), "message", "local_parser")]))
    malformed = [value for value in email.received_headers if "from " not in value.lower() or " by " not in value.lower()]
    if malformed:
        findings.append(Finding("HEADER-002", "HEADER", "Received header is inconsistent", "A Received header does not contain the expected routing structure.", "MEDIUM", 10, 0.8, [Evidence("header", malformed[0], "Received", "local_parser", "This indicates formatting inconsistency, not exact origin.")]))
    return findings