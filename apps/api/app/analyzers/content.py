"""Basic deterministic social-engineering/content heuristics."""

import re

from app.intake.parser import ParsedEmail

from .types import Evidence, Finding


def analyze_content(email: ParsedEmail) -> list[Finding]:
    text = re.sub(r"<[^>]+>", " ", email.body_text or email.body_html or "")
    lowered = text.lower()
    findings: list[Finding] = []
    urgency = re.search(r"urgent|immediately|within \d+ hours?|account.{0,20}(locked|suspend)", lowered)
    credentials = re.search(r"password|verify your account|login|credential|one[- ]time code|otp", lowered)
    if urgency:
        findings.append(Finding("CONTENT-001", "CONTENT", "Urgency language", "The message contains urgency or account-pressure language.", "MEDIUM", 10, 0.75, [Evidence("body_text", urgency.group(0), "body", "local_heuristic")]))
    if credentials:
        findings.append(Finding("CONTENT-002", "CONTENT", "Credential request language", "The message contains language associated with credential or account requests.", "MEDIUM", 15, 0.75, [Evidence("body_text", credentials.group(0), "body", "local_heuristic")]))
    return findings