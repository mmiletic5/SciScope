"""Versioned token estimation interfaces."""

from __future__ import annotations

from typing import Protocol


class TokenCounter(Protocol):
    """Estimate tokens for a complete embedding input."""

    counter_id: str

    def count(self, text: str) -> int:
        """Return the estimated token count."""
        ...


class Utf8BytesDiv3Counter:
    """Estimate one token per three UTF-8 bytes, rounded upward."""

    counter_id = "utf8-bytes-div3-v1"

    def count(self, text: str) -> int:
        """Count estimated tokens for text."""
        return (len(text.encode("utf-8")) + 2) // 3
