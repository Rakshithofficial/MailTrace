"""Sender and reply-routing checks."""

from email.utils import parseaddr
from app.intake.parser import ParsedEmail

from .types import Evidence, Finding


def _domain(address: str | None) -> str:
    return (address or "").rsplit("@", 1)[-1].lower().rstrip(".") if "@" in (address or "") else ""


def analyze_sender(email: ParsedEmail) -> list[Finding]:
    findings: list[Finding] = []
    if not email.sender or not parseaddr(email.sender)[1] or "@" not in email.sender:
        findings.append(Finding("SENDER-001", "SENDER", "Malformed sender address", "The From address is missing or malformed.", "MEDIUM", 10, 0.98, [Evidence("address", email.sender or "", "From", "local_parser")]))
        return findings

    sender_domain = _domain(email.sender)
    reply_domain = _domain(email.reply_to)
    if email.reply_to and reply_domain and reply_domain != sender_domain:
        findings.append(Finding("SENDER-003", "SENDER", "Reply-To domain differs", "Reply-To routes to a different domain than From.", "MEDIUM", 10, 0.95, [Evidence("address", f"From={email.sender}; Reply-To={email.reply_to}", "headers", "local_parser")]))

    display = (email.sender_display_name or "").lower()
    brand_domains = {"microsoft", "office", "paypal", "google", "apple", "amazon"}
    if any(brand in display for brand in brand_domains) and not any(brand in sender_domain for brand in brand_domains):
        findings.append(Finding("SENDER-002", "SENDER", "Display name and domain differ", "The visible organization does not match the sender domain.", "MEDIUM", 10, 0.85, [Evidence("address", f"display={email.sender_display_name}; domain={sender_domain}", "From", "local_parser")]))
    return findings