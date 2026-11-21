"""Opaque request-ID validation and generation for Feature 011."""

import re
import secrets

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def generate_request_id() -> str:
    """Generate an opaque request ID that satisfies the public contract.

    Returns:
        A URL-safe opaque identifier accepted by the request-ID policy.
    """
    return secrets.token_urlsafe(18)


def is_valid_request_id(value: object) -> bool:
    """Return whether a value is a valid public request ID.

    Args:
        value: Candidate value supplied by a caller or internal component.

    Returns:
        True when the value is a string matching the approved ID pattern.
    """
    return (
        isinstance(value, str)
        and REQUEST_ID_PATTERN.fullmatch(value) is not None
    )
