"""Pure paper builder interfaces; implementation deferred to Phase 2."""

from collections.abc import Sequence


class PaperBuildError(ValueError):
    """Collected paper problems represented only by sorted sanitized codes.

    Attributes:
        codes: Sorted unique codes, without input values or identifiers.
    """

    codes: tuple[str, ...]

    def __init__(self, codes: Sequence[str]) -> None:
        """Initialize an error from the finalized plan's code vocabulary.

        Args:
            codes: Collected failure codes to sanitize, deduplicate and sort.
        """
        raise NotImplementedError


def derive_publication_year(date_text: str) -> int:
    """Derive the leading year from valid year, year-month, or full date text.

    Args:
        date_text: An F001 publication date at one of its supported precisions.

    Returns:
        The leading four digits as an integer, without a 1600 minimum.

    Raises:
        PaperBuildError: If date precision, calendar date, or year is invalid.
    """
    raise NotImplementedError


def build_papers(
    metadata_records: Sequence[object],
    manifest_records: Sequence[object],
) -> tuple[dict[str, object], ...]:
    """Join unique normalized DOI sets, preserving approved raw field values.

    Args:
        metadata_records: Parsed F001 metadata records, never mutated.
        manifest_records: Parsed F001 acquisition records, never mutated.

    Returns:
        Paper dictionaries in DOI order and the plan's exact field order.

    Raises:
        PaperBuildError: After collecting all safely detectable join and
            validation problems using sorted sanitized codes.
    """
    raise NotImplementedError
