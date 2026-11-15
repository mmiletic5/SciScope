"""Normalize DOI spellings while retaining the original input."""

import re
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

_DOI_PATTERN = re.compile(r"^10\.[0-9]{4,9}/\S+$")
_PREFIXES = (
    "doi:",
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "info:doi/",
)


@dataclass(frozen=True)
class NormalizedDoi:
    """A normalized DOI and its untouched source value."""

    doi: str
    original_doi: str


def _extract_url_id(value: str) -> str:
    """Extract exactly one URL id parameter, decoding it once."""
    parsed = urlsplit(value)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("Malformed URL DOI source")
    ids = [
        part[3:] for part in parsed.query.split("&") if part.startswith("id=")
    ]
    if len(ids) != 1 or not ids[0]:
        raise ValueError("URL must contain exactly one nonempty id parameter")
    return unquote(ids[0])


def normalize_doi(original: str) -> NormalizedDoi:
    """Normalize one DOI using the approved pilot rules.

    Args:
        original: Original DOI spelling or URL containing an id parameter.

    Returns:
        Normalized DOI together with the untouched original value.

    Raises:
        ValueError: If the value is missing, ambiguous, or invalid.
    """
    value = original.strip()
    lowered = value.lower()
    for prefix in _PREFIXES:
        if lowered.startswith(prefix):
            value = value[len(prefix) :]
            break
    else:
        if lowered.startswith(("http://", "https://")):
            value = _extract_url_id(value)

    value = value.strip()
    while value and value[-1] in ".,;":
        value = value[:-1]
    while value and value[-1] in ")]":
        closer = value[-1]
        opener = "(" if closer == ")" else "["
        if value.count(closer) <= value.count(opener):
            break
        value = value[:-1]
        while value and value[-1] in ".,;":
            value = value[:-1]

    value = value.lower()
    if not _DOI_PATTERN.fullmatch(value):
        raise ValueError(f"Invalid DOI: {original!r}")
    return NormalizedDoi(doi=value, original_doi=original)
