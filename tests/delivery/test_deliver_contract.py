"""SYNTHETIC offline T001 RED tests without keys, network, or article prose."""

from __future__ import annotations

import ast
import inspect
import json
from collections.abc import Callable, Iterator
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from delivery_fixtures import (
    ENTITIES,
    FACTORIES,
    MUTATIONS,
    Mutation,
    Record,
    chunk,
    section,
    valid_records,
)
from jsonschema import Draft202012Validator

from sciscope.chunking.output import CHUNK_RECORD_FIELDS
from sciscope.delivery import contract
from sciscope.embedding import store
from sciscope.jats import cli as jats_cli

ROOT = Path(__file__).resolve().parents[2]
GOOD = valid_records()
CHECKERS: dict[str, Callable[[object], tuple[str, ...]]] = {
    "paper": contract.check_paper,
    "section": contract.check_section,
    "chunk": contract.check_chunk,
    "embedding_set": contract.check_embedding_set,
    "embedding_manifest": contract.check_embedding_manifest,
    "delivery_manifest": contract.check_delivery_manifest,
}
SUFFIXES = (
    "missing-field",
    "extra-field",
    "bad-type",
    "bad-value",
    "bad-pattern",
)
ROOT_FIELDS = {
    "schema_version",
    "contract_version",
    "status",
    "counts",
    "files",
    "processing_versions",
    "source_reports",
    "embedding_set",
}


@pytest.fixture
def schema() -> dict[str, Any]:
    """Load the one committed schema, without resolving network references."""
    return json.loads((ROOT / "docs/DATA_CONTRACT.json").read_text("utf-8"))


def _validator(schema: dict[str, Any], entity: str) -> Draft202012Validator:
    """Wrap local definitions and clearly reject the old schema root shape."""
    assert set(schema["properties"]) == ROOT_FIELDS, "old schema root shape"
    assert all(
        node["$ref"].startswith("#/$defs/")
        for node in _objects(schema)
        if "$ref" in node
    )
    if entity == "delivery_manifest":
        return Draft202012Validator(schema)
    assert entity in schema["$defs"], f"missing local definition: {entity}"
    return Draft202012Validator(
        {
            "$schema": schema["$schema"],
            "$ref": f"#/$defs/{entity}",
            "$defs": schema["$defs"],
        }
    )


def _objects(value: object) -> Iterator[dict[str, Any]]:
    """Walk schema dictionaries to inspect local references only."""
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _objects(item)
    elif isinstance(value, list):
        for item in value:
            yield from _objects(item)


def test_schema_is_valid_draft_2020_12(schema: dict[str, Any]) -> None:
    """Check the actual document dialect and metaschema validity."""
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    Draft202012Validator.check_schema(schema)


def test_schema_root_and_local_definitions(schema: dict[str, Any]) -> None:
    """Require delivery root and all nine reusable child definitions."""
    assert set(schema["properties"]) == ROOT_FIELDS
    assert set(schema["required"]) == ROOT_FIELDS
    assert schema["additionalProperties"] is False
    assert set(FACTORIES) - {"delivery_manifest"} <= schema["$defs"].keys()
    for node in _objects(schema):
        if "$ref" in node:
            assert node["$ref"].startswith("#/$defs/")
            assert node["$ref"][len("#/$defs/") :] in schema["$defs"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", "0.3.0"),
        ("contract_version", "0.3.0"),
        ("status", "draft"),
    ],
)
def test_manifest_constants(
    schema: dict[str, Any], field: str, value: str
) -> None:
    """Require constant versions and draft status in the root contract."""
    assert field in schema["properties"], "old schema root shape"
    assert schema["properties"][field].get("const") == value


@pytest.mark.parametrize("entity,record", GOOD)
def test_schema_accepts_synthetic_records(
    schema: dict[str, Any],
    entity: str,
    record: Record,
) -> None:
    """Accept fresh flat records and all deliberately legal edge cases."""
    assert _validator(schema, entity).is_valid(record)
    if entity == "delivery_manifest":
        assert Draft202012Validator(schema).is_valid(record)


@pytest.mark.parametrize(
    "entity,record", [item for item in GOOD if item[0] in CHECKERS]
)
def test_runtime_accepts_synthetic_records(entity: str, record: Record) -> None:
    """Return an empty tuple for valid structures without mutating them."""
    before = deepcopy(record)
    assert CHECKERS[entity](record) == ()
    assert record == before


@pytest.mark.parametrize(
    "mutation", MUTATIONS, ids=lambda item: f"{item.entity}-{item.name}"
)
def test_schema_mutation_verdict(
    schema: dict[str, Any],
    mutation: Mutation,
) -> None:
    """Assert the tagged schema verdict, including documented C3 exceptions."""
    record = FACTORIES[mutation.entity]()
    mutation.apply(record)
    assert _validator(schema, mutation.entity).is_valid(record) is (
        mutation.schema_accepts
    )


@pytest.mark.parametrize(
    "mutation", MUTATIONS, ids=lambda item: f"{item.entity}-{item.name}"
)
def test_runtime_mutation_verdict(mutation: Mutation) -> None:
    """Assert tagged runtime verdicts and a sorted, unique, safe vocabulary."""
    record = FACTORIES[mutation.entity]()
    mutation.apply(record)
    before = deepcopy(record)
    codes = CHECKERS[mutation.entity](record)
    assert type(codes) is tuple
    assert codes == tuple(sorted(set(codes)))
    assert (not codes) is mutation.runtime_accepts
    assert set(codes) <= {f"{mutation.entity}-{suffix}" for suffix in SUFFIXES}
    assert record == before


@pytest.mark.parametrize("entity", ENTITIES)
@pytest.mark.parametrize("bad", [None, [], "SYNTHETIC secret/path", 1, True])
def test_runtime_never_raises_on_non_objects(entity: str, bad: object) -> None:
    """Reject arbitrary parsed JSON roots using only the entity type code."""
    assert CHECKERS[entity](bad) == (f"{entity}-bad-type",)


@pytest.mark.parametrize("entity", ENTITIES)
def test_runtime_collects_unique_independent_codes(entity: str) -> None:
    """Collect repeated type failures once with missing and extra fields."""
    row = FACTORIES[entity]()
    fields = list(row)
    del row[fields[0]]
    row[fields[1]] = {"SYNTHETIC-sensitive": "SYNTHETIC value"}
    row[fields[2]] = {"SYNTHETIC-sensitive": "SYNTHETIC value"}
    row["SYNTHETIC-extra"] = "SYNTHETIC /private/value"
    assert CHECKERS[entity](row) == tuple(
        sorted(
            (
                f"{entity}-missing-field",
                f"{entity}-extra-field",
                f"{entity}-bad-type",
            )
        )
    )


def test_fixture_fields_match_real_chunk_writer() -> None:
    """Guard the exact writer order rather than duplicating its field list."""
    assert tuple(chunk()) == CHUNK_RECORD_FIELDS
    assert tuple(chunk()["spans"][0]) == (
        "source_locator",
        "paragraph_index",
        "start",
        "end",
    )


def test_fixture_fields_match_real_section_writer() -> None:
    """Extract field literals from the actual writer without modifying it."""
    module = ast.parse(inspect.getsource(jats_cli))
    writer = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "_section_rows"
    )
    dictionaries = [
        node for node in ast.walk(writer) if isinstance(node, ast.Dict)
    ]
    assert len(dictionaries) == 1
    keys = tuple(ast.literal_eval(key) for key in dictionaries[0].keys)
    assert tuple(section()) == keys


def test_fixture_fields_match_real_embedding_manifest_writer() -> None:
    """Extract the fixed field set from F003's actual manifest writer."""
    module = ast.parse(inspect.getsource(store.build_manifest))
    returned = next(
        node.value for node in ast.walk(module) if isinstance(node, ast.Return)
    )
    assert isinstance(returned, ast.Dict)
    assert tuple(FACTORIES["embedding_manifest"]()) == tuple(
        ast.literal_eval(key) for key in returned.keys
    )


@pytest.mark.parametrize("entity", tuple(FACTORIES))
def test_factories_return_fresh_nested_records(entity: str) -> None:
    """Ensure a caller's nested mutations cannot contaminate later tests."""
    first, second = FACTORIES[entity](), FACTORIES[entity]()
    assert first == second and first is not second
    for key, value in first.items():
        if isinstance(value, (dict, list)):
            assert value is not second[key]


def test_only_integral_floats_have_documented_divergent_verdicts() -> None:
    """Keep C3 differences explicit and out of T004's future parity subset."""
    divergent = [
        case
        for case in MUTATIONS
        if case.schema_accepts != case.runtime_accepts
    ]
    assert divergent
    assert all(
        "DOCUMENTED-C3" in case.name
        and case.schema_accepts
        and not case.runtime_accepts
        for case in divergent
    )
    assert len({(case.entity, case.name) for case in MUTATIONS}) == len(
        MUTATIONS
    )
