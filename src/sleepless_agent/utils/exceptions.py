"""Custom exceptions for Sleepless Agent"""

from __future__ import annotations

from datetime import datetime
from typing import Optional


class PauseException(Exception):
    """Raised when Pro plan usage limit requires task execution pause"""

    def __init__(
        self,
        message: str,
        reset_time: Optional[datetime],
        usage_percent: float,
    ) -> None:
        """Initialize PauseException

        Args:
            message: Exception message
            reset_time: When usage limit will reset
            usage_percent: Usage percentage reported by CLI
        """
        super().__init__(message)
        self.reset_time: Optional[datetime] = reset_time
        self.usage_percent: float = usage_percent

    def __str__(self) -> str:
        """Return string representation of the exception."""
        return super().__str__()

    def __repr__(self) -> str:
        """Return detailed representation of the exception."""
        return f"PauseException(message={super().__str__()!r}, reset_time={self.reset_time!r}, usage_percent={self.usage_percent!r})"
