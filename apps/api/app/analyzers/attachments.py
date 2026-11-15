"""Attachment metadata checks; attachment bytes are never executed."""

from pathlib import PurePath

from app.intake.parser import ParsedEmail

from .types import Evidence, Finding

RISKY_EXTENSIONS = {".exe", ".scr", ".js", ".vbs", ".ps1", ".bat", ".cmd", ".docm", ".xlsm", ".pptm", ".iso", ".img", ".zip", ".rar"}


def analyze_attachments(email: ParsedEmail) -> list[Finding]:
    findings: list[Finding] = []
    for attachment in email.attachments:
        filename = str(attachment.get("filename") or "unnamed")
        suffixes = [suffix.lower() for suffix in PurePath(filename).suffixes]
        evidence = [Evidence("attachment", f"{filename}; sha256={attachment.get('sha256', '')}", "attachment", "local_parser")]
        if len(suffixes) > 1 and suffixes[-1] in {".exe", ".js", ".scr", ".vbs"}:
            findings.append(Finding("ATTACH-001", "ATTACHMENT", "Misleading attachment filename", "The attachment uses multiple extensions ending in an executable or script type.", "HIGH", 10, 0.95, evidence))
        elif suffixes and suffixes[-1] in RISKY_EXTENSIONS:
            findings.append(Finding("ATTACH-002", "ATTACHMENT", "High-risk attachment type", "The attachment has a type that requires cautious handling.", "HIGH", 15, 0.95, evidence))
    return findings