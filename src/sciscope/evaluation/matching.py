"""Exact DOI/locator evidence-unit identity and retrieval matching."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sciscope.plos_pilot.doi import normalize_doi


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    """One annotated source passage used as a retrieval gold unit."""

    doi: str
    section: str
    source_locator: str
    relevance_label: int
    quotation: str | None = None

    @property
    def unit_id(self) -> str:
        """Return a deterministic identity for this DOI/locator/quotation."""
        doi = normalize_doi(self.doi).doi
        quote_hash = (
            hashlib.sha256(self.quotation.encode("utf-8")).hexdigest()
            if self.quotation is not None
            else ""
        )
        parts = (doi, self.source_locator, quote_hash)
        encoded = bytearray()
        for part in parts:
            value = part.encode("utf-8")
            encoded.extend(len(value).to_bytes(8, "big"))
            encoded.extend(value)
        return hashlib.sha256(bytes(encoded)).hexdigest()


@dataclass(frozen=True, slots=True)
class RetrievedEvidence:
    """One ranked result with exact locator and text provenance."""

    chunk_id: str
    doi: str
    section_path: tuple[str, ...]
    source_locator: str
    span_locators: tuple[str, ...]
    text: str


@dataclass(frozen=True, slots=True)
class MatchingResult:
    """Unique positive gold units and earliest matching ranks."""

    relevant_unit_ids: frozenset[str]
    first_rank_by_unit: Mapping[str, int]
    duplicate_chunk_ids: tuple[str, ...]


def match_evidence_units(
    references: Sequence[EvidenceReference],
    retrieved: Sequence[RetrievedEvidence],
) -> MatchingResult:
    """Match ranked results to unique gold evidence units.

    Primary matching requires normalized DOI and an exact primary/span locator.
    The sole fallback requires the same DOI, exact labeled section, and exact
    quotation containment. Repeated or overlapping results can only preserve
    the earliest rank for a unit; they cannot increase its count.

    Args:
        references: Annotated gold passages with labels 0 through 3.
        retrieved: Ordered retrieval results; positions are one-based ranks.

    Returns:
        Positive canonical unit IDs and their earliest matching ranks.

    Raises:
        ValueError: If labels, identities, annotations, or results conflict.
    """
    unique: dict[str, EvidenceReference] = {}
    for reference in references:
        _validate_reference(reference)
        identity = reference.unit_id
        prior = unique.get(identity)
        if (
            prior is not None
            and prior.relevance_label != reference.relevance_label
        ):
            raise ValueError("conflicting relevance labels for canonical unit")
        unique.setdefault(identity, reference)

    relevant = frozenset(
        identity
        for identity, reference in unique.items()
        if reference.relevance_label in (2, 3)
    )
    first_rank: dict[str, int] = {}
    seen_chunk: dict[str, RetrievedEvidence] = {}
    duplicate_ids: list[str] = []
    for rank, candidate in enumerate(retrieved, start=1):
        _validate_retrieved(candidate)
        previous = seen_chunk.get(candidate.chunk_id)
        if previous is not None:
            if previous != candidate:
                raise ValueError("duplicate chunk ID has conflicting content")
            duplicate_ids.append(candidate.chunk_id)
            continue
        seen_chunk[candidate.chunk_id] = candidate
        candidate_doi = normalize_doi(candidate.doi).doi
        candidate_locators = {
            candidate.source_locator,
            *candidate.span_locators,
        }
        candidate_section = " > ".join(candidate.section_path)
        for identity in relevant:
            reference = unique[identity]
            if normalize_doi(reference.doi).doi != candidate_doi:
                continue
            exact = reference.source_locator in candidate_locators
            fallback = (
                not exact
                and reference.quotation is not None
                and reference.section == candidate_section
                and reference.quotation in candidate.text
            )
            if exact or fallback:
                first_rank.setdefault(identity, rank)

    return MatchingResult(relevant, first_rank, tuple(duplicate_ids))


def _validate_reference(reference: EvidenceReference) -> None:
    if not isinstance(reference, EvidenceReference):
        raise ValueError("gold reference must be an EvidenceReference")
    if not reference.section.strip() or not reference.source_locator.strip():
        raise ValueError("gold section and locator must be nonempty")
    if isinstance(
        reference.relevance_label, bool
    ) or reference.relevance_label not in (0, 1, 2, 3):
        raise ValueError("relevance label must be 0, 1, 2, or 3")
    if reference.quotation is not None and not reference.quotation:
        raise ValueError("quotation must be nonempty when supplied")
    normalize_doi(reference.doi)


def _validate_retrieved(candidate: RetrievedEvidence) -> None:
    values = (
        candidate.chunk_id,
        candidate.doi,
        candidate.source_locator,
        candidate.text,
    )
    if any(not isinstance(value, str) or not value for value in values):
        raise ValueError(
            "retrieved identity, locator, and text must be nonempty"
        )
    if any(
        not isinstance(item, str) or not item
        for item in candidate.span_locators
    ):
        raise ValueError("span locators must be nonempty strings")
    if any(
        not isinstance(item, str) or not item for item in candidate.section_path
    ):
        raise ValueError("section path must contain nonempty strings")
    normalize_doi(candidate.doi)
