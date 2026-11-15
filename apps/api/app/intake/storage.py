"""Quarantined raw-message storage; attachments remain metadata-only."""

from pathlib import Path
from uuid import uuid4


def store_raw_email(raw_bytes: bytes, root: Path) -> str:
    root.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4()}.eml"
    destination = root / filename
    destination.write_bytes(raw_bytes)
    return str(destination)


def remove_raw_email(reference: str) -> None:
    path = Path(reference)
    if path.exists() and path.is_file():
        path.unlink()
