"""Declarative flat F001–F003 checks with no I/O or runtime dependencies."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from sciscope.chunking.validate import (
    is_json_integer,
    is_json_number,
    is_json_string,
)

HASH_PATTERN = re.compile(r"^[0-9a-f]{64}(?![\s\S])$")
DOI_PATTERN = re.compile(r"^10\.[0-9]{4,9}/\S+(?![\s\S])$")
LOCATOR_PATTERN = re.compile(
    r"^jats:v1:[0-9a-f]{64}:(?:/[^\W\d][\w\.-]*\[[1-9][0-9]*\])+"
    r"(?![\s\S])$"
)
PUBLICATION_DATE_PATTERN = re.compile(
    r"^[0-9]{4}(?:-[0-9]{2}(?:-[0-9]{2})?)?(?![\s\S])$"
)
RETRIEVED_AT_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?\+00:00(?![\s\S])$"
)
CREATION_DATE_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}(?![\s\S])$")


@dataclass(frozen=True, slots=True)
class _Field:
    """One structural field rule used by the declarative entity tables."""

    kind: str
    description: str = ""
    nullable: bool = False
    minimum: int | float | None = None
    exclusive_minimum: int | float | None = None
    maximum: int | float | None = None
    min_length: int = 0
    pattern: re.Pattern[str] | None = None
    values: tuple[str, ...] = ()
    fields: Mapping[str, _Field] | None = None
    item: _Field | None = None
    min_items: int = 0


def _object(fields: Mapping[str, _Field], description: str = "") -> _Field:
    """Describe a fixed required field set with no additional properties."""
    return _Field("object", description=description, fields=fields)


def _array(item: _Field, minimum: int = 0, description: str = "") -> _Field:
    """Describe an ordered JSON array with independently checked elements."""
    return _Field(
        "array", item=item, min_items=minimum, description=description
    )


def _constant(value: str, description: str = "") -> _Field:
    """Describe a string constant without accepting coerced types."""
    return _Field("string", values=(value,), description=description)


_TEXT = _Field("string", min_length=1)
_EMPTY_TEXT = _Field("string")
_COUNT = _Field(
    "integer", minimum=0, description="Written as integer literals, never 1.0."
)
_POSITIVE = _Field(
    "integer", minimum=1, description="Written as integer literals, never 1.0."
)
_NUMBER = _Field("number")
_BOOL = _Field("boolean")
_HASH = _Field("string", pattern=HASH_PATTERN)
_DOI = _Field(
    "string",
    pattern=DOI_PATTERN,
    description=(
        "F001 normalization: sciscope.plos_pilot.doi.normalize_doi (approved "
        "prefixes, trimming/punctuation and lowercase); normalization "
        "consistency "
        "is semantic. Local XML: data/raw/plos/ + quote(doi, safe='') + .xml."
    ),
)
_LOCATOR = _Field(
    "string",
    pattern=LOCATOR_PATTERN,
    description=(
        "Locator v1: jats:v1:<64 lowercase hex> followed by /name[index] "
        "components; Unicode name grammar [^\\W\\d][\\w\\.-]*, positive "
        "indices without leading zeros. locator_digest alone does not validate "
        "the path; root/traversal depend on the source document."
    ),
)
_PATH = _array(
    _TEXT, 1, "Ordered headings; (untitled) means no heading, never display it."
)
_TAXONOMY = _Field(
    "string",
    values=(
        "abstract",
        "introduction",
        "methods",
        "results",
        "results_discussion",
        "discussion",
        "conclusions",
        "other",
    ),
    description=(
        "Taxonomy v0: abstracts always abstract; body precedence is exact "
        "normalized heading > sec-type > nearest explicit ancestor > other. "
        "Mappings and heading normalization are in sciscope.jats.classify."
    ),
)
_AUTHOR = _object({"surname": _TEXT, "given_names": _EMPTY_TEXT})
_PAPER = _object(
    {
        "doi": _DOI,
        "title": _TEXT,
        "authors": _array(_AUTHOR, 1),
        "journal": _TEXT,
        "publication_date": _Field(
            "string",
            pattern=PUBLICATION_DATE_PATTERN,
            description=(
                "ASCII year/year-month/full-date shape; "
                "calendar checked by builder."
            ),
        ),
        "article_type": _TEXT,
        "subjects": _array(_TEXT),
        "license": _Field(
            "string",
            min_length=1,
            description="Raw license string; no normalization.",
        ),
        "language": _Field(
            "string",
            min_length=1,
            description=(
                "Raw language; EN and en both occur. "
                "Compare case-insensitively."
            ),
        ),
        "source_url": _TEXT,
        "retrieved_at": _Field("string", pattern=RETRIEVED_AT_PATTERN),
        "xml_sha256": _HASH,
        "publication_year": _POSITIVE,
    },
    "Flat paper; publication_year is the only derived metadata field.",
)
PAPER_FIELDS = tuple(cast(Mapping[str, _Field], _PAPER.fields))

_SECTION = _object(
    {
        "doi": _DOI,
        "title": _TEXT,
        "xml_sha256": _HASH,
        "section_id": _TEXT,
        "parent_section_id": _Field("string", nullable=True, min_length=1),
        "section_path": _PATH,
        "original_heading": _EMPTY_TEXT,
        "normalized_type": _TAXONOMY,
        "source_locator": _LOCATOR,
        "depth": _POSITIVE,
        "paragraph_count": _COUNT,
    },
    "Flat F002 section; paragraph_count counts own direct p, including empty.",
)
_SPAN = _object(
    {
        "source_locator": _LOCATOR,
        "paragraph_index": _POSITIVE,
        "start": _COUNT,
        "end": _POSITIVE,
    },
    "Half-open Unicode code-point offsets; end > start is semantic (T005).",
)
_CHUNK = _object(
    {
        "chunk_id": _HASH,
        "doi": _DOI,
        "xml_sha256": _HASH,
        "section_id": _TEXT,
        "ordinal": _POSITIVE,
        "chunk_kind": _constant("paragraph"),
        "normalized_type": _TAXONOMY,
        "section_path": _PATH,
        "text": _TEXT,
        "text_sha256": _HASH,
        "spans": _array(_SPAN, 1),
        "source_locator": _LOCATOR,
        "content_tokens": _POSITIVE,
        "hard_split": _BOOL,
        "omitted": _array(
            _TEXT,
            description="Raw omitted XML element names, not count objects.",
        ),
        "chunking_version": _constant("chunking-v1"),
        "token_counter_id": _constant("utf8-bytes-div3-v1"),
        "template_version": _constant("embedding-text-v1"),
    },
    "Flat F003 chunk; hashes and source consistency are checked semantically.",
)
_NORMALIZATION_FIELDS = {
    "declared": _constant("l2"),
    "observed_norm_min": _NUMBER,
    "observed_norm_max": _NUMBER,
}
_EMBEDDING_SET = _object(
    {
        "provider": _TEXT,
        "model": _TEXT,
        "dimensions": _POSITIVE,
        "dtype": _constant("float32-le"),
        "row_mapping": _constant(
            "embedding_manifest.entries",
            "Vector row i belongs ONLY to "
            "embedding_manifest.entries[i].chunk_id; "
            "never use position in chunks.jsonl.",
        ),
        "passage_prefix": _EMPTY_TEXT,
        "query_prefix": _EMPTY_TEXT,
        "normalization": _object(
            {
                **_NORMALIZATION_FIELDS,
                "tolerance": _Field("number", exclusive_minimum=0, maximum=1),
            }
        ),
        "chunks_sha256": _HASH,
        "vectors_sha256": _HASH,
        "embedding_model_revision": _Field(
            "string",
            nullable=True,
            min_length=1,
            description="Null when not applicable; never invent a revision.",
        ),
    },
    "Queries must use the same provider, model, dimensions and query_prefix.",
)
_EMBEDDING_MANIFEST = _object(
    {
        "format_version": _constant("embedding-set-v1"),
        "status": _Field("string", values=("complete", "partial")),
        "provider": _TEXT,
        "model": _TEXT,
        "requested_dimensions": _POSITIVE,
        "returned_dimensions": _POSITIVE,
        "normalization": _object(_NORMALIZATION_FIELDS),
        "passage_prefix": _EMPTY_TEXT,
        "query_prefix": _EMPTY_TEXT,
        "template_version": _constant("embedding-text-v1"),
        "token_counter_id": _constant("utf8-bytes-div3-v1"),
        "chunking_version": _constant("chunking-v1"),
        "chunks_sha256": _HASH,
        "chunk_count": _COUNT,
        "vector_count": _COUNT,
        "creation_date": _Field("string", pattern=CREATION_DATE_PATTERN),
        "usage": _object({"prompt_tokens": _COUNT, "total_tokens": _COUNT}),
        "estimated_input_tokens": _COUNT,
        "provider_input_count": _COUNT,
        "custom_base_url_used": _BOOL,
        "vectors_file": _constant("vectors.f32"),
        "vectors_dtype": _constant("float32-le"),
        "vectors_sha256": _HASH,
        "entries": _array(_object({"chunk_id": _HASH, "input_sha256": _HASH})),
    },
    "Unchanged F003 manifest shape; delivery rejects partial sets separately.",
)
_FILE_DESCRIPTOR = _object(
    {
        "sha256": _HASH,
        "bytes": _COUNT,
        "record_count": _COUNT,
    }
)
_SOURCE_REPORT_DESCRIPTOR = _object({"sha256": _HASH, "bytes": _COUNT})
_INFORMATIONAL_HASH = _Field(
    "string",
    pattern=HASH_PATTERN,
    description=(
        "Informational source_sha256; never compare with local source files."
    ),
)
_PROCESSING_VERSIONS = _object(
    {
        "parser": _object(
            {
                "version": _Field("string", nullable=True, min_length=1),
                "source_sha256": _INFORMATIONAL_HASH,
            }
        ),
        "taxonomy": _object(
            {"version": _constant("v0"), "source_sha256": _INFORMATIONAL_HASH}
        ),
        "locator": _constant("jats:v1"),
        "chunking_version": _constant("chunking-v1"),
        "token_counter_id": _constant("utf8-bytes-div3-v1"),
        "template_version": _constant("embedding-text-v1"),
    }
)
_DELIVERY_MANIFEST = _object(
    {
        "schema_version": _constant("0.3.0"),
        "contract_version": _constant("0.3.0"),
        "status": _constant("draft"),
        "counts": _object(
            {"papers": _COUNT, "sections": _COUNT, "chunks": _COUNT}
        ),
        "files": _object(
            dict.fromkeys(
                (
                    "papers.jsonl",
                    "sections.jsonl",
                    "chunks.jsonl",
                    "vectors.f32",
                    "embedding_manifest.json",
                ),
                _FILE_DESCRIPTOR,
            )
        ),
        "processing_versions": _PROCESSING_VERSIONS,
        "source_reports": _object(
            dict.fromkeys(
                (
                    "parse_report.json",
                    "chunk_report.json",
                    "embedding_report.json",
                ),
                _SOURCE_REPORT_DESCRIPTOR,
            )
        ),
        "embedding_set": _EMBEDDING_SET,
    }
)


def _check(value: object, spec: _Field, entity: str) -> tuple[str, ...]:
    """Walk finite field specifications, collecting safe structure codes."""
    failures: set[str] = set()
    pending = [(value, spec)]
    while pending:
        item, rule = pending.pop()
        if item is None and rule.nullable:
            continue
        if not _has_type(item, rule.kind):
            failures.add("bad-type")
            continue
        if rule.kind == "object":
            row = cast(dict[str, object], item)
            fields = rule.fields or {}
            if fields.keys() - row.keys():
                failures.add("missing-field")
            if row.keys() - fields.keys():
                failures.add("extra-field")
            pending.extend(
                (row[key], field) for key, field in fields.items() if key in row
            )
        elif rule.kind == "array":
            array = cast(list[object], item)
            if len(array) < rule.min_items:
                failures.add("bad-value")
            if rule.item is not None:
                pending.extend((child, rule.item) for child in array)
        elif rule.kind == "string":
            text = cast(str, item)
            if len(text) < rule.min_length or (
                rule.values and text not in rule.values
            ):
                failures.add("bad-value")
            if rule.pattern is not None and rule.pattern.search(text) is None:
                failures.add("bad-pattern")
        elif rule.kind in ("integer", "number"):
            number = cast(int | float, item)
            if (
                (rule.minimum is not None and number < rule.minimum)
                or (
                    rule.exclusive_minimum is not None
                    and number <= rule.exclusive_minimum
                )
                or (rule.maximum is not None and number > rule.maximum)
            ):
                failures.add("bad-value")
    return tuple(sorted(f"{entity}-{suffix}" for suffix in failures))


def _has_type(value: object, kind: str) -> bool:
    """Apply existing strict JSON primitive predicates before value checks."""
    if kind == "string":
        return is_json_string(value)
    if kind == "integer":
        return is_json_integer(value)
    if kind == "number":
        return is_json_number(value)
    if kind == "boolean":
        return type(value) is bool
    if kind == "array":
        return isinstance(value, list)
    return isinstance(value, dict)


def _paper_field_codes(field: str, value: object) -> tuple[str, ...]:
    """Reuse one paper field rule, including missing nested author fields."""
    fields = cast(Mapping[str, _Field], _PAPER.fields)
    return _check(value, fields[field], "paper")


def check_paper(value: object) -> tuple[str, ...]:
    """Return sorted unique paper structure codes, or an empty valid tuple."""
    return _check(value, _PAPER, "paper")


def check_section(value: object) -> tuple[str, ...]:
    """Return sorted unique F002 section codes without cross-record checks."""
    return _check(value, _SECTION, "section")


def check_chunk(value: object) -> tuple[str, ...]:
    """Return sorted unique F003 chunk/span structure codes without mutation."""
    return _check(value, _CHUNK, "chunk")


def check_embedding_set(value: object) -> tuple[str, ...]:
    """Return sorted unique set metadata codes without loading vectors."""
    return _check(value, _EMBEDDING_SET, "embedding_set")


def check_embedding_manifest(value: object) -> tuple[str, ...]:
    """Return F003 manifest codes, accepting complete or partial structures."""
    return _check(value, _EMBEDDING_MANIFEST, "embedding_manifest")


def check_delivery_manifest(value: object) -> tuple[str, ...]:
    """Return sorted unique delivery metadata codes without file access."""
    return _check(value, _DELIVERY_MANIFEST, "delivery_manifest")
