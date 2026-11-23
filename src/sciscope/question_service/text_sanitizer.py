"""Removal of leaked chunk ids from model-written free text.

Citations belong only in ``citation_chunk_ids``. Models sometimes also write
raw 64-hex chunk ids, usually in brackets, inside prose. ``strip_chunk_ids``
removes them; ordinary short bracketed numbers such as ``[20]`` are kept.
"""

from __future__ import annotations

import re
from typing import Final

_HEX_ID: Final = r"[0-9a-fA-F]{64}"
_SEP: Final = r"[\s,;]*"
# A bracket or parenthesis group holding only ids and separators.
_GROUP: Final = re.compile(rf"[\[(]{_SEP}(?:{_HEX_ID}{_SEP})+[\])]")
# A bare id, not part of a longer hexadecimal run.
_BARE: Final = re.compile(rf"(?<![0-9a-fA-F])({_HEX_ID})(?![0-9a-fA-F])")
_EMPTY_BRACKETS: Final = re.compile(r"[\[(]\s*[\])]")
_SPACES: Final = re.compile(r"[ \t\f\v]+")
_SPACE_BEFORE_PUNCT: Final = re.compile(r"[ \t]+([.,;:!?])")
_BLANK_LINES: Final = re.compile(r"\s*\n\s*")


def strip_chunk_ids(text: str) -> str:
    """Remove 64-hex ids, with their brackets, from ``text``.

    Args:
        text: Model-supplied free text.

    Returns:
        The text without ids or the empty brackets they leave behind, with
        whitespace collapsed and no space before punctuation. Empty when
        nothing else remains.
    """
    cleaned = _GROUP.sub(" ", text)
    cleaned = _BARE.sub(" ", cleaned)
    cleaned = _EMPTY_BRACKETS.sub(" ", cleaned)
    cleaned = _BLANK_LINES.sub(" ", cleaned)
    cleaned = _SPACES.sub(" ", cleaned)
    cleaned = _SPACE_BEFORE_PUNCT.sub(r"\1", cleaned)
    return cleaned.strip()
