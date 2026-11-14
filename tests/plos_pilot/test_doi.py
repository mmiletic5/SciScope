"""Synthetic DOI normalization behavior checks."""

import pytest

from sciscope.plos_pilot.doi import normalize_doi


@pytest.mark.parametrize(
    ("original", "expected"),
    [
        ("10.9999/SYNTHETIC", "10.9999/synthetic"),
        (" 10.9999/SYNTHETIC ", "10.9999/synthetic"),
        ("doi:10.9999/SYNTHETIC", "10.9999/synthetic"),
        ("https://doi.org/10.9999/SYNTHETIC", "10.9999/synthetic"),
        ("http://doi.org/10.9999/SYNTHETIC", "10.9999/synthetic"),
        ("https://dx.doi.org/10.9999/SYNTHETIC", "10.9999/synthetic"),
        ("info:doi/10.9999/SYNTHETIC", "10.9999/synthetic"),
        ("10.9999/SYNTHETIC.,;", "10.9999/synthetic"),
        ("10.9999/SYNTHETIC)", "10.9999/synthetic"),
        ("10.9999/SYNTHETIC]", "10.9999/synthetic"),
        ("10.9999/(SYNTHETIC)", "10.9999/(synthetic)"),
        ("10.9999/[SYNTHETIC]", "10.9999/[synthetic]"),
        (
            "https://journals.plos.org/plosone/article?id=10.9999%2FSYNTHETIC",
            "10.9999/synthetic",
        ),
        ("10.9999/SYNTHETIC.2", "10.9999/synthetic.2"),
    ],
)
def test_normalizes_and_preserves_original(
    original: str, expected: str
) -> None:
    """Every supported spelling retains its untouched source value."""
    result = normalize_doi(original)
    assert result.doi == expected
    assert result.original_doi == original


@pytest.mark.parametrize(
    "original",
    [
        "10.999/SYNTHETIC",
        "10.9999999999/SYNTHETIC",
        "10.9999/",
        "10.9999/SYN THETIC",
        "https://journals.plos.org/plosone/article?other=10.9999%2FSYNTHETIC",
        "https://journals.plos.org/plosone/article?id=10.9999%2Fa&id=10.9999%2Fb",
        "https://journals.plos.org/plosone/article?id=10.9999%252FSYNTHETIC",
    ],
)
def test_rejects_malformed_and_ambiguous_values(original: str) -> None:
    """Malformed DOI syntax and ambiguous URL IDs are rejected."""
    with pytest.raises(ValueError):
        normalize_doi(original)
