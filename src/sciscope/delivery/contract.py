"""Pure structural checker interfaces; implementation deferred to Phase 2.

Checkers will reuse sciscope.chunking.validate.is_json_string,
is_json_integer, and is_json_number. They return sorted unique entity codes,
never raise for malformed JSON values, and never echo input values.
"""


def check_paper(value: object) -> tuple[str, ...]:
    """Check a parsed paper against the flat v0.3 structure.

    Args:
        value: Any parsed JSON value, including malformed record roots.

    Returns:
        Sorted unique paper structure codes; empty for a valid record.
    """
    raise NotImplementedError


def check_section(value: object) -> tuple[str, ...]:
    """Check a parsed section against the real F002 field set.

    Args:
        value: Any parsed JSON value, including malformed record roots.

    Returns:
        Sorted unique section structure codes; empty for a valid record.
    """
    raise NotImplementedError


def check_chunk(value: object) -> tuple[str, ...]:
    """Check a parsed chunk and nested spans against the real F003 field set.

    Args:
        value: Any parsed JSON value, including malformed record roots.

    Returns:
        Sorted unique chunk structure codes; empty for a valid record.
    """
    raise NotImplementedError


def check_embedding_set(value: object) -> tuple[str, ...]:
    """Check provider metadata without loading vectors or comparing records.

    Args:
        value: Any parsed JSON value, including malformed record roots.

    Returns:
        Sorted unique embedding_set structure codes; empty when valid.
    """
    raise NotImplementedError


def check_embedding_manifest(value: object) -> tuple[str, ...]:
    """Check the fixed F003 writer shape, including entries and usage.

    Args:
        value: Any parsed JSON value, including malformed record roots.

    Returns:
        Sorted unique embedding_manifest structure codes; empty when valid.
    """
    raise NotImplementedError


def check_delivery_manifest(value: object) -> tuple[str, ...]:
    """Check the draft delivery manifest and its nested metadata descriptors.

    Args:
        value: Any parsed JSON value, including malformed record roots.

    Returns:
        Sorted unique delivery_manifest structure codes; empty when valid.
    """
    raise NotImplementedError
