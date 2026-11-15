"""MailTrace database package."""

from .base import Base
from .session import create_engine_from_url, get_session_factory

__all__ = ["Base", "create_engine_from_url", "get_session_factory"]
