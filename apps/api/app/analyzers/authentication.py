"""Authentication-result checks based only on explicitly present headers."""

from app.intake.parser import ParsedEmail

from .types import Evidence, Finding


def analyze_authentication(email: ParsedEmail) -> list[Finding]:
    findings: list[Finding] = []
    for result in email.authentication_results:
        lowered = result.lower()
        evidence = [Evidence("header", result, "Authentication-Results", "local_parser", "Authentication headers are reported evidence and are not independently verified.")]
        if "spf=fail" in lowered or "spf=softfail" in lowered:
            findings.append(Finding("AUTH-001", "AUTHENTICATION", "SPF failure", "The message contains an explicit SPF fail or softfail result.", "HIGH", 15, 0.9, evidence))
        if "dkim=fail" in lowered:
            findings.append(Finding("AUTH-002", "AUTHENTICATION", "DKIM failure", "The message contains an explicit DKIM failure result.", "MEDIUM", 10, 0.9, evidence))
        if "dmarc=fail" in lowered:
            findings.append(Finding("AUTH-003", "AUTHENTICATION", "DMARC failure", "The message contains an explicit DMARC failure result.", "HIGH", 15, 0.9, evidence))
    return findings