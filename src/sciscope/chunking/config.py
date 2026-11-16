"""Chunk limits and embedding text template interfaces."""

from __future__ import annotations

from dataclasses import dataclass

from sciscope.chunking.counter import TokenCounter

ABSOLUTE_CEILING_TOKENS = 512
TEMPLATE_VERSION = "embedding-text-v1"
HEADING_SEPARATOR = " > "
CONTEXT_TEXT_SEPARATOR = "\n\n"
UNTITLED_LABEL = "(untitled)"


class ChunkingError(ValueError):
    """A source or chunking constraint is invalid."""


class ConfigError(ChunkingError):
    """Chunk configuration is invalid."""


class HeadingBudgetError(ChunkingError):
    """Heading context leaves too little content space."""


@dataclass(frozen=True, slots=True)
class ChunkConfig:
    """Token limits for deterministic section chunking."""

    operational_cap_tokens: int = 384
    content_target_min_tokens: int = 200
    content_target_max_tokens: int = 350
    soft_min_tokens: int = 50
    prefix_reserve_tokens: int = 0
    min_content_budget_tokens: int = 32

    def __post_init__(self) -> None:
        """Validate the configured limits."""
        self._validate()

    def _validate(self) -> None:
        """Reject invalid token limits."""
        raise NotImplementedError("T001")


def heading_context(section_path: tuple[str, ...]) -> str:
    """Build context from meaningful section headings."""
    raise NotImplementedError("T001")


def build_embedding_text(
    section_path: tuple[str, ...], chunk_text: str, prefix: str = ""
) -> str:
    """Build the final versioned embedding input."""
    raise NotImplementedError("T001")


def content_budget(
    config: ChunkConfig,
    counter: TokenCounter,
    section_path: tuple[str, ...],
) -> int:
    """Return content capacity after prefix and heading overhead."""
    raise NotImplementedError("T001")
