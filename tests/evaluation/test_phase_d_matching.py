"""Independent synthetic oracles for evidence identity and matching."""

from __future__ import annotations

import pytest

from sciscope.evaluation.matching import (
    EvidenceReference,
    RetrievedEvidence,
    match_evidence_units,
)


def _reference(
    locator: str,
    *,
    doi: str = "10.1234/synthetic",
    label: int = 3,
    quote: str | None = None,
) -> EvidenceReference:
    return EvidenceReference(
        doi=doi,
        section="Results",
        source_locator=locator,
        relevance_label=label,
        quotation=quote,
    )


def _retrieved(
    chunk_id: str,
    locator: str,
    *,
    text: str = "Synthetic results support the claim.",
    spans: tuple[str, ...] = (),
    doi: str = "10.1234/synthetic",
) -> RetrievedEvidence:
    return RetrievedEvidence(
        chunk_id=chunk_id,
        doi=doi,
        section_path=("Results",),
        source_locator=locator,
        span_locators=spans,
        text=text,
    )


def test_one_retrieved_chunk_can_match_multiple_independent_gold_units() -> (
    None
):
    """A chunk credits two distinct units only by matching each locator."""
    references = (
        _reference("Results/p1"),
        _reference("Results/p2"),
        _reference("Results/p3"),
    )
    retrieved = (_retrieved("c1", "Results/p1", spans=("Results/p2",)),)

    result = match_evidence_units(references, retrieved)

    assert result.relevant_unit_ids == frozenset(
        {references[0].unit_id, references[1].unit_id, references[2].unit_id}
    )
    assert result.first_rank_by_unit == {
        references[0].unit_id: 1,
        references[1].unit_id: 1,
    }


def test_many_chunks_for_one_unit_count_once_at_earliest_original_rank() -> (
    None
):
    """Repeated locator matches do not multiply evidence or compress ranks."""
    reference = _reference("Results/p1")
    retrieved = (
        _retrieved("c1", "elsewhere"),
        _retrieved("c2", "Results/p1"),
        _retrieved("c3", "Results/p1"),
    )

    result = match_evidence_units((reference,), retrieved)

    assert result.first_rank_by_unit == {reference.unit_id: 2}


def test_doi_normalization_and_exact_locator_are_required() -> None:
    """DOI URLs normalize, but approximate locators never become positive."""
    reference = _reference(
        "Results/p1", doi="https://doi.org/10.1234/Synthetic"
    )
    wrong_locator = _retrieved("c1", "Results/p10")

    result = match_evidence_units((reference,), (wrong_locator,))

    assert not result.first_rank_by_unit


def test_doi_url_and_case_normalize_for_exact_primary_locator_match() -> None:
    """DOI spelling differences do not block an exact locator match."""
    reference = _reference(
        "Results/p1", doi="https://doi.org/10.1234/Synthetic"
    )
    retrieved = _retrieved("c1", "Results/p1", doi="10.1234/synthetic")

    result = match_evidence_units((reference,), (retrieved,))

    assert result.first_rank_by_unit == {reference.unit_id: 1}


def test_exact_duplicate_gold_annotations_collapse_before_denominator() -> None:
    """Repeated annotations for one canonical quote do not double gold count."""
    reference = _reference("Results/p1", quote="Exact synthetic quote.")

    result = match_evidence_units((reference, reference), ())

    assert result.relevant_unit_ids == frozenset({reference.unit_id})


def test_identical_duplicate_chunk_ids_preserve_first_rank_only() -> None:
    """Repeated identical retrieval rows are diagnosed and counted once."""
    reference = _reference("Results/p1")
    duplicate = _retrieved("c1", "Results/p1")

    result = match_evidence_units((reference,), (duplicate, duplicate))

    assert result.first_rank_by_unit == {reference.unit_id: 1}
    assert result.duplicate_chunk_ids == ("c1",)


def test_same_locator_distinct_quotes_have_distinct_gold_unit_identity() -> (
    None
):
    """Quote hashes distinguish source claims at a shared paragraph locator."""
    first = _reference("Results/p1", quote="First exact statement.")
    second = _reference("Results/p1", quote="Second exact statement.")

    result = match_evidence_units((first, second), ())

    assert first.unit_id != second.unit_id
    assert len(result.relevant_unit_ids) == 2


def test_quote_fallback_requires_same_doi_section_and_exact_containment() -> (
    None
):
    """The controlled fallback rejects section-only and approximate matches."""
    reference = _reference(
        "missing-locator", quote="The treatment reduced symptoms by 20%."
    )
    exact = _retrieved(
        "c1",
        "another-locator",
        text="The treatment reduced symptoms by 20%. The study was small.",
    )
    wrong_section = RetrievedEvidence(
        chunk_id="c2",
        doi="10.1234/synthetic",
        section_path=("Methods",),
        source_locator="another-locator",
        span_locators=(),
        text="The treatment reduced symptoms by 20%.",
    )
    approximate = _retrieved(
        "c3", "another-locator", text="The treatment reduced symptoms by 19%."
    )

    result = match_evidence_units(
        (reference,), (exact, wrong_section, approximate)
    )

    assert result.first_rank_by_unit == {reference.unit_id: 1}


def test_duplicate_or_overlapping_chunks_do_not_inflate_gold_unit_counts() -> (
    None
):
    """A unit is counted once regardless of duplicate retrieved evidence."""
    reference = _reference("Results/p1")
    retrieved = (
        _retrieved("c1", "Results/p1"),
        _retrieved("c2", "Results/p1"),
        _retrieved("c3", "Results/p1", spans=("Results/p1",)),
    )

    result = match_evidence_units((reference,), retrieved)

    assert len(result.first_rank_by_unit) == 1
    assert result.first_rank_by_unit[reference.unit_id] == 1


def test_conflicting_labels_for_one_canonical_unit_fail_closed() -> None:
    """Conflicting labels cannot be settled by annotation order."""
    with pytest.raises(ValueError, match="conflicting"):
        match_evidence_units(
            (
                _reference("Results/p1", label=3),
                _reference("Results/p1", label=1),
            ),
            (),
        )
