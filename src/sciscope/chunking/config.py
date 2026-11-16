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
        if not 1 <= self.operational_cap_tokens <= ABSOLUTE_CEILING_TOKENS:
            raise ConfigError("invalid-operational-cap")
        if not 0 <= self.prefix_reserve_tokens < self.operational_cap_tokens:
            raise ConfigError("invalid-prefix-reserve")
        if not (
            1
            <= self.content_target_min_tokens
            <= self.content_target_max_tokens
        ):
            raise ConfigError("invalid-content-targets")
        if self.soft_min_tokens < 0:
            raise ConfigError("invalid-soft-minimum")
        if self.min_content_budget_tokens < 1:
            raise ConfigError("invalid-content-budget-minimum")


def heading_context(section_path: tuple[str, ...]) -> str:
    """Build context from meaningful section headings."""
    return HEADING_SEPARATOR.join(
        heading
        for heading in section_path
        if heading.strip() and heading != UNTITLED_LABEL
    )


def build_embedding_text(
    section_path: tuple[str, ...], chunk_text: str, prefix: str = ""
) -> str:
    """Build the final versioned embedding input."""
    context = heading_context(section_path)
    if context:
        return prefix + context + CONTEXT_TEXT_SEPARATOR + chunk_text
    return prefix + chunk_text


def content_budget(
    config: ChunkConfig,
    counter: TokenCounter,
    section_path: tuple[str, ...],
) -> int:
    """Return content capacity after prefix and heading overhead."""
    context = heading_context(section_path)
    overhead = counter.count(context + CONTEXT_TEXT_SEPARATOR) if context else 0
    budget = (
        config.operational_cap_tokens - config.prefix_reserve_tokens - overhead
    )
    if budget < config.min_content_budget_tokens:
        raise HeadingBudgetError("heading-budget-exhausted")
    return budget
