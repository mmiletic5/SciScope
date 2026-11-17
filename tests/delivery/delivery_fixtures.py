"""Fresh SYNTHETIC offline records with invented text and no article prose."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

type Record = dict[str, Any]

DIGEST = "a" * 64
DOI = "10.1234/synthetic.a"
LOCATOR = f"jats:v1:{DIGEST}:/article[1]/body[1]/sec[1]"
PAPER_FIELDS = (
    "doi",
    "title",
    "authors",
    "journal",
    "publication_date",
    "article_type",
    "subjects",
    "license",
    "language",
    "source_url",
    "retrieved_at",
    "xml_sha256",
    "publication_year",
)


def paper() -> Record:
    """Return a fresh SYNTHETIC paper with raw metadata and provenance."""
    return {
        "doi": DOI,
        "title": "SYNTHETIC: imaginary lantern experiment",
        "authors": [{"surname": "Synthetic", "given_names": ""}],
        "journal": "SYNTHETIC Journal",
        "publication_date": "2024-02-29",
        "article_type": "research-article",
        "subjects": ["Research Article", "SYNTHETIC Z", "SYNTHETIC A"],
        "license": "SYNTHETIC permission statement",
        "language": "EN",
        "source_url": "https://example.invalid/synthetic.xml",
        "retrieved_at": "2026-11-17T12:00:00+00:00",
        "xml_sha256": DIGEST,
        "publication_year": 2024,
    }


def metadata() -> Record:
    """Return SYNTHETIC F001 metadata including excluded invented text."""
    result = {
        key: value
        for key, value in paper().items()
        if key
        not in ("source_url", "retrieved_at", "xml_sha256", "publication_year")
    }
    result["abstract"] = "SYNTHETIC: invented abstract, excluded from papers."
    return result


def acquisition_manifest() -> Record:
    """Return a fresh SYNTHETIC acquisition row, including excluded fields."""
    row = paper()
    return {
        "doi": DOI,
        "original_doi": "DOI:10.1234/SYNTHETIC.A",
        **{
            key: row[key]
            for key in ("source_url", "retrieved_at", "xml_sha256", "license")
        },
        "raw_xml_path": "data/raw/plos/SYNTHETIC.xml",
        "query_provenance": [],
    }


def section() -> Record:
    """Return a fresh SYNTHETIC zero-own-text section with a Unicode heading."""
    return {
        "doi": DOI,
        "title": paper()["title"],
        "xml_sha256": DIGEST,
        "section_id": f"{DOI}#sec-1",
        "parent_section_id": None,
        "section_path": ["SYNTHETIC Δ lanterns"],
        "original_heading": "SYNTHETIC Δ lanterns",
        "normalized_type": "other",
        "source_locator": LOCATOR,
        "depth": 1,
        "paragraph_count": 0,
    }


def chunk() -> Record:
    """Return a fresh SYNTHETIC chunk with LF and Unicode code-point offsets."""
    text = "SYNTHETIC: a violet lantern.\nΔ\u0085\u2028\u2029"
    locator = LOCATOR + "/p[1]"
    return {
        "chunk_id": "b" * 64,
        "doi": DOI,
        "xml_sha256": DIGEST,
        "section_id": section()["section_id"],
        "ordinal": 1,
        "chunk_kind": "paragraph",
        "normalized_type": "other",
        "section_path": section()["section_path"],
        "text": text,
        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "spans": [
            {
                "source_locator": locator,
                "paragraph_index": 1,
                "start": 0,
                "end": len(text),
            }
        ],
        "source_locator": locator,
        "content_tokens": 12,
        "hard_split": False,
        "omitted": [],
        "chunking_version": "chunking-v1",
        "token_counter_id": "utf8-bytes-div3-v1",
        "template_version": "embedding-text-v1",
    }


def embedding_set() -> Record:
    """Return fresh SYNTHETIC provider metadata with nullable model revision."""
    return {
        "provider": "synthetic",
        "model": "SYNTHETIC-model",
        "dimensions": 2,
        "dtype": "float32-le",
        "row_mapping": "embedding_manifest.entries",
        "passage_prefix": "",
        "query_prefix": "",
        "normalization": {
            "declared": "l2",
            "observed_norm_min": 1.0,
            "observed_norm_max": 1.0,
            "tolerance": 0.01,
        },
        "chunks_sha256": DIGEST,
        "vectors_sha256": DIGEST,
        "embedding_model_revision": None,
    }


def span() -> Record:
    """Return a fresh SYNTHETIC half-open Unicode code-point span."""
    return chunk()["spans"][0]


def embedding_manifest() -> Record:
    """Return the fixed F003 manifest writer shape with SYNTHETIC values."""
    return {
        "format_version": "embedding-set-v1",
        "status": "complete",
        "provider": "synthetic",
        "model": "SYNTHETIC-model",
        "requested_dimensions": 2,
        "returned_dimensions": 2,
        "normalization": {
            "declared": "l2",
            "observed_norm_min": 1.0,
            "observed_norm_max": 1.0,
        },
        "passage_prefix": "",
        "query_prefix": "",
        "template_version": "embedding-text-v1",
        "token_counter_id": "utf8-bytes-div3-v1",
        "chunking_version": "chunking-v1",
        "chunks_sha256": DIGEST,
        "chunk_count": 1,
        "vector_count": 1,
        "creation_date": "2026-11-17",
        "usage": {"prompt_tokens": 1, "total_tokens": 1},
        "estimated_input_tokens": 12,
        "provider_input_count": 1,
        "custom_base_url_used": False,
        "vectors_file": "vectors.f32",
        "vectors_dtype": "float32-le",
        "vectors_sha256": DIGEST,
        "entries": [{"chunk_id": chunk()["chunk_id"], "input_sha256": DIGEST}],
    }


def file_descriptor() -> Record:
    """Return a fresh SYNTHETIC payload descriptor without a path."""
    return {"sha256": DIGEST, "bytes": 8, "record_count": 1}


def source_report_descriptor() -> Record:
    """Return a fresh SYNTHETIC repository report descriptor."""
    return {"sha256": DIGEST, "bytes": 8}


def processing_versions() -> Record:
    """Return fresh approved version identifiers and informational hashes."""
    return {
        "parser": {"version": None, "source_sha256": DIGEST},
        "taxonomy": {"version": "v0", "source_sha256": DIGEST},
        "locator": "jats:v1",
        "chunking_version": "chunking-v1",
        "token_counter_id": "utf8-bytes-div3-v1",
        "template_version": "embedding-text-v1",
    }


def delivery_manifest() -> Record:
    """Return a fresh SYNTHETIC draft manifest with five payload descriptors."""
    return {
        "schema_version": "0.3.0",
        "contract_version": "0.3.0",
        "status": "draft",
        "counts": {"papers": 1, "sections": 1, "chunks": 1},
        "files": {
            name: file_descriptor()
            for name in (
                "papers.jsonl",
                "sections.jsonl",
                "chunks.jsonl",
                "vectors.f32",
                "embedding_manifest.json",
            )
        },
        "processing_versions": processing_versions(),
        "source_reports": {
            name: source_report_descriptor()
            for name in (
                "parse_report.json",
                "chunk_report.json",
                "embedding_report.json",
            )
        },
        "embedding_set": embedding_set(),
    }


FACTORIES: dict[str, Callable[[], Record]] = {
    "paper": paper,
    "section": section,
    "chunk": chunk,
    "embedding_set": embedding_set,
    "embedding_manifest": embedding_manifest,
    "delivery_manifest": delivery_manifest,
    "file_descriptor": file_descriptor,
    "source_report_descriptor": source_report_descriptor,
    "processing_versions": processing_versions,
    "span": span,
}
ENTITIES = tuple(FACTORIES)[:6]


def valid_records() -> tuple[tuple[str, Record], ...]:
    """Return fresh good entities and approved SYNTHETIC edge cases."""
    lower = paper()
    lower.update(language="en", license="https://example.invalid/license")
    mixed = paper()
    mixed["language"] = "sYnThEtIc"
    early = paper()
    early.update(publication_date="1500", publication_year=1500)
    microsecond_paper = paper()
    microsecond_paper["retrieved_at"] = "2026-11-15T09:26:53.481027+00:00"
    split_chunk = chunk()
    split_chunk.update(hard_split=True, omitted=["fig", "table-wrap"])
    implicit = section()
    implicit.update(
        section_id=f"{DOI}#body-p-1",
        original_heading="",
        section_path=["(untitled)"],
        paragraph_count=1,
        source_locator=f"jats:v1:{DIGEST}:/article[1]/body[1]/p[1]",
    )
    abstract = section()
    abstract.update(
        section_id=f"{DOI}#abstract.1",
        parent_section_id=f"{DOI}#abstract",
        section_path=["(untitled)", "SYNTHETIC Aim"],
        depth=2,
        normalized_type="abstract",
        original_heading="SYNTHETIC Aim",
        source_locator=f"jats:v1:{DIGEST}:/article[1]/front[1]/"
        "article-meta[1]/abstract[1]/sec[1]",
    )
    unicode_locator = section()
    unicode_locator["source_locator"] = LOCATOR + "/Δelta.name-x[2]"
    taxonomy_records: list[tuple[str, Record]] = []
    for normalized_type in (
        "abstract",
        "introduction",
        "methods",
        "results",
        "results_discussion",
        "discussion",
        "conclusions",
        "other",
    ):
        for entity in ("section", "chunk"):
            row = FACTORIES[entity]()
            row["normalized_type"] = normalized_type
            taxonomy_records.append((entity, row))
    return (
        *((entity, FACTORIES[entity]()) for entity in FACTORIES),
        ("paper", lower),
        ("paper", mixed),
        ("paper", early),
        ("paper", microsecond_paper),
        ("chunk", split_chunk),
        ("section", implicit),
        ("section", abstract),
        ("section", unicode_locator),
        *taxonomy_records,
    )


def replace(
    path: tuple[str | int, ...], value: object
) -> Callable[[Record], None]:
    """Build a mutation of one nested field, without sharing a record."""

    def apply(record: Record) -> None:
        target: Any = record
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = deepcopy(value)

    return apply


def remove(field: str | tuple[str | int, ...]) -> Callable[[Record], None]:
    """Build a mutation removing one required top-level or nested field."""
    path = (field,) if isinstance(field, str) else field

    def apply(record: Record) -> None:
        target: Any = record
        for key in path[:-1]:
            target = target[key]
        del target[path[-1]]

    return apply


@dataclass(frozen=True, slots=True)
class Mutation:
    """A SYNTHETIC verdict; integral floats are DOCUMENTED C3 divergences."""

    name: str
    entity: str
    apply: Callable[[Record], None]
    schema_accepts: bool
    runtime_accepts: bool


def _mutations() -> tuple[Mutation, ...]:
    """Build the shared structure corpus without performing validation."""
    cases: list[Mutation] = []

    def add(
        entity: str,
        name: str,
        path: tuple[str | int, ...],
        value: object,
        schema: bool = False,
        runtime: bool = False,
    ) -> None:
        cases.append(
            Mutation(name, entity, replace(path, value), schema, runtime)
        )

    for entity in ENTITIES:
        field = next(iter(FACTORIES[entity]()))
        cases.append(
            Mutation("missing-field", entity, remove(field), False, False)
        )
        add(entity, "extra-field", ("SYNTHETIC-extra",), "SYNTHETIC")
        add(entity, "wrong-type", (field,), [])
        add(entity, "forbidden-null", (field,), None)
    for entity, field in (
        ("paper", "publication_year"),
        ("section", "depth"),
        ("chunk", "ordinal"),
        ("embedding_set", "dimensions"),
        ("embedding_manifest", "requested_dimensions"),
    ):
        add(entity, "boolean-as-integer", (field,), True)
        original = FACTORIES[entity]()[field]
        add(
            entity,
            "integral-float-DOCUMENTED-C3",
            (field,),
            float(original),
            True,
            False,
        )
        add(entity, "fractional-number", (field,), 1.5)
    for field in ("title", "journal", "article_type", "license", "language"):
        add("paper", f"empty-{field}", (field,), "")
    add("paper", "empty-authors", ("authors",), [])
    add("paper", "author-wrong-type", ("authors", 0), "SYNTHETIC")
    add("paper", "empty-surname", ("authors", 0, "surname"), "")
    add("paper", "given-names-null", ("authors", 0, "given_names"), None)
    add(
        "paper",
        "empty-given-names-allowed",
        ("authors", 0, "given_names"),
        "",
        True,
        True,
    )
    add("chunk", "empty-text", ("text",), "")
    add("chunk", "unknown-chunk-kind", ("chunk_kind",), "SYNTHETIC-unknown")
    for entity in ("section", "chunk"):
        add(
            entity,
            "bad-taxonomy-enum",
            ("normalized_type",),
            "SYNTHETIC-unknown",
        )
    for field in ("schema_version", "contract_version"):
        add("delivery_manifest", f"wrong-{field}", (field,), "0.2.0")
    add("delivery_manifest", "status-not-draft", ("status",), "approved")
    add("delivery_manifest", "boolean-count", ("counts", "papers"), True)
    add(
        "delivery_manifest",
        "integral-float-count-DOCUMENTED-C3",
        ("counts", "papers"),
        1.0,
        True,
        False,
    )
    add("embedding_set", "dimensions-zero", ("dimensions",), 0)
    add("embedding_set", "dimensions-negative", ("dimensions",), -1)
    for field in ("requested_dimensions", "returned_dimensions"):
        add("embedding_manifest", f"{field}-string-mismatch", (field,), "2")
        add("embedding_manifest", f"{field}-zero", (field,), 0)
    for name, path, value in (
        ("span-end-equals-zero-start", ("spans", 0, "end"), 0),
        ("span-end-before-start", ("spans", 0, "end"), -1),
        ("span-negative-start", ("spans", 0, "start"), -1),
        ("span-zero-index", ("spans", 0, "paragraph_index"), 0),
        ("span-boolean-index", ("spans", 0, "paragraph_index"), True),
        ("span-extra", ("spans", 0, "extra"), "SYNTHETIC"),
    ):
        add("chunk", name, path, value)
    pattern_fields = (
        ("paper", ("doi",), DOI, "doi"),
        ("section", ("doi",), DOI, "doi"),
        ("chunk", ("doi",), DOI, "doi"),
        ("paper", ("publication_date",), "2024-02-29", "date"),
        ("paper", ("retrieved_at",), paper()["retrieved_at"], "date"),
        ("embedding_manifest", ("creation_date",), "2026-11-17", "date"),
        *(
            (entity, (field,), FACTORIES[entity]()[field], "hash")
            for entity, field in (
                ("paper", "xml_sha256"),
                ("section", "xml_sha256"),
                ("chunk", "xml_sha256"),
                ("chunk", "chunk_id"),
                ("chunk", "text_sha256"),
                ("embedding_set", "chunks_sha256"),
                ("embedding_set", "vectors_sha256"),
                ("embedding_manifest", "chunks_sha256"),
                ("embedding_manifest", "vectors_sha256"),
            )
        ),
        ("embedding_manifest", ("entries", 0, "chunk_id"), "b" * 64, "hash"),
        ("embedding_manifest", ("entries", 0, "input_sha256"), DIGEST, "hash"),
        ("section", ("source_locator",), LOCATOR, "locator"),
        ("chunk", ("source_locator",), chunk()["source_locator"], "locator"),
        (
            "chunk",
            ("spans", 0, "source_locator"),
            chunk()["spans"][0]["source_locator"],
            "locator",
        ),
        *(
            ("delivery_manifest", ("files", name, "sha256"), DIGEST, "hash")
            for name in delivery_manifest()["files"]
        ),
        *(
            (
                "delivery_manifest",
                ("source_reports", name, "sha256"),
                DIGEST,
                "hash",
            )
            for name in delivery_manifest()["source_reports"]
        ),
        *(
            (
                "delivery_manifest",
                ("processing_versions", name, "source_sha256"),
                DIGEST,
                "hash",
            )
            for name in ("parser", "taxonomy")
        ),
        *(
            ("delivery_manifest", ("embedding_set", field), DIGEST, "hash")
            for field in ("chunks_sha256", "vectors_sha256")
        ),
    )
    for entity, path, good, kind in pattern_fields:
        label = "-".join(map(str, path))
        add(entity, f"{label}-trailing-LF", path, good + "\n")
        if kind == "hash":
            add(entity, f"{label}-uppercase", path, good.upper())
            add(entity, f"{label}-short", path, good[:-1])
        elif kind == "doi":
            add(entity, f"{label}-bad-doi", path, "11.1234/SYNTHETIC")
        elif kind == "locator":
            for name, bad in (
                ("uppercase-digest", good.replace(DIGEST, DIGEST.upper())),
                ("zero-index", good.replace("sec[1]", "sec[0]")),
                ("leading-zero", good.replace("sec[1]", "sec[01]")),
                ("bad-component", good.replace("sec[1]", "9sec[1]")),
            ):
                add(entity, f"{label}-{name}", path, bad)
    # Phase 1b: structure-only boundaries verified against the real writers.
    for name, path, value in (
        ("depth-zero", ("depth",), 0),
        ("depth-negative", ("depth",), -1),
        ("paragraph-count-negative", ("paragraph_count",), -1),
        ("section-path-empty", ("section_path",), []),
        ("section-path-empty-element", ("section_path",), [""]),
        ("original-heading-null", ("original_heading",), None),
        ("parent-section-id-number", ("parent_section_id",), 1),
        ("section-id-empty", ("section_id",), ""),
        ("title-empty", ("title",), ""),
    ):
        add("section", name, path, value)
    for name, path, value in (
        ("ordinal-zero", ("ordinal",), 0),
        ("content-tokens-negative", ("content_tokens",), -1),
        ("content-tokens-zero", ("content_tokens",), 0),
        ("hard-split-string", ("hard_split",), "true"),
        ("omitted-object", ("omitted",), {"fig": 1}),
        ("omitted-object-element", ("omitted",), [{"kind": "fig"}]),
        ("omitted-integer-element", ("omitted",), [1]),
        ("spans-empty", ("spans",), []),
    ):
        add("chunk", name, path, value)
    for field in ("chunking_version", "token_counter_id", "template_version"):
        add("chunk", f"{field}-empty", (field,), "")

    def missing(entity: str, name: str, path: tuple[str | int, ...]) -> None:
        cases.append(Mutation(name, entity, remove(path), False, False))

    for name in delivery_manifest()["files"]:
        missing("delivery_manifest", f"files-missing-{name}", ("files", name))
        for field in ("bytes", "record_count"):
            add(
                "delivery_manifest",
                f"files-{name}-{field}-negative",
                ("files", name, field),
                -1,
            )
    for name in ("SYNTHETIC-extra.json", "delivery_manifest.json"):
        add(
            "delivery_manifest",
            f"files-extra-{name}",
            ("files", name),
            file_descriptor(),
        )
    for name in delivery_manifest()["source_reports"]:
        missing(
            "delivery_manifest",
            f"source-reports-missing-{name}",
            ("source_reports", name),
        )
        add(
            "delivery_manifest",
            f"source-reports-{name}-bytes-negative",
            ("source_reports", name, "bytes"),
            -1,
        )
    add(
        "delivery_manifest",
        "source-reports-extra",
        ("source_reports", "SYNTHETIC-extra.json"),
        source_report_descriptor(),
    )
    for field in ("papers", "sections", "chunks"):
        add(
            "delivery_manifest",
            f"counts-{field}-negative",
            ("counts", field),
            -1,
        )
    add(
        "delivery_manifest",
        "processing-locator-other-version",
        ("processing_versions", "locator"),
        "jats:v2",
    )
    add(
        "delivery_manifest",
        "processing-parser-extra-key",
        ("processing_versions", "parser", "SYNTHETIC-extra"),
        "SYNTHETIC",
    )
    add(
        "delivery_manifest",
        "processing-taxonomy-version-empty",
        ("processing_versions", "taxonomy", "version"),
        "",
    )
    add(
        "delivery_manifest",
        "processing-parser-version-null-allowed",
        ("processing_versions", "parser", "version"),
        None,
        True,
        True,
    )
    add(
        "delivery_manifest",
        "processing-parser-version-string-allowed",
        ("processing_versions", "parser", "version"),
        "SYNTHETIC-parser-v1",
        True,
        True,
    )

    for name, path, value in (
        ("dtype-other", ("dtype",), "float64-le"),
        ("row-mapping-other", ("row_mapping",), "chunks.jsonl.lines"),
        ("normalization-declared-other", ("normalization", "declared"), "none"),
        ("normalization-tolerance-zero", ("normalization", "tolerance"), 0),
        (
            "normalization-tolerance-negative",
            ("normalization", "tolerance"),
            -1,
        ),
        (
            "observed-norm-min-string",
            ("normalization", "observed_norm_min"),
            "1",
        ),
        (
            "observed-norm-max-string",
            ("normalization", "observed_norm_max"),
            "1",
        ),
        ("provider-empty", ("provider",), ""),
        ("model-empty", ("model",), ""),
        ("model-revision-empty", ("embedding_model_revision",), ""),
    ):
        add("embedding_set", name, path, value)
    for name, field, value in (
        (
            "model-revision-string-allowed",
            "embedding_model_revision",
            "SYNTHETIC-model-v1",
        ),
        ("passage-prefix-empty-allowed", "passage_prefix", ""),
        ("query-prefix-empty-allowed", "query_prefix", ""),
    ):
        add("embedding_set", name, (field,), value, True, True)

    for status in ("complete", "partial"):
        add(
            "embedding_manifest",
            f"status-{status}-allowed",
            ("status",),
            status,
            True,
            True,
        )
    for status in ("draft", "SYNTHETIC-unknown", ""):
        add(
            "embedding_manifest",
            f"status-{status!r}-invalid",
            ("status",),
            status,
        )
    for field in ("chunk_id", "input_sha256"):
        missing(
            "embedding_manifest",
            f"entry-missing-{field}",
            ("entries", 0, field),
        )
    add(
        "embedding_manifest",
        "entry-extra-field",
        ("entries", 0, "SYNTHETIC-extra"),
        "SYNTHETIC",
    )
    add("embedding_manifest", "usage-array", ("usage",), [])
    missing(
        "embedding_manifest",
        "usage-missing-prompt-tokens",
        ("usage", "prompt_tokens"),
    )
    add(
        "embedding_manifest",
        "usage-extra-field",
        ("usage", "SYNTHETIC-extra"),
        1,
    )
    add(
        "embedding_manifest",
        "custom-base-url-string",
        ("custom_base_url_used",),
        "false",
    )

    for name, path, value in (
        ("publication-date-word", ("publication_date",), "yesterday"),
        ("publication-date-unpadded-month", ("publication_date",), "2024-1"),
        ("publication-date-short-year", ("publication_date",), "24"),
        ("publication-year-zero", ("publication_year",), 0),
        ("publication-year-negative", ("publication_year",), -1),
        ("retrieved-at-not-date", ("retrieved_at",), "not-a-date"),
        ("source-url-empty", ("source_url",), ""),
        ("subjects-empty-element", ("subjects",), [""]),
        ("subjects-non-string-element", ("subjects",), [1]),
    ):
        add("paper", name, path, value)
    for name, path, value in (
        (
            "publication-date-calendar-deferred-allowed",
            ("publication_date",),
            "2024-13",
        ),
        ("publication-year-one-allowed", ("publication_year",), 1),
        ("subjects-empty-array-allowed", ("subjects",), []),
    ):
        add("paper", name, path, value, True, True)
    return tuple(cases)


MUTATIONS = _mutations()
