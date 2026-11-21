"""Test-only ASGI adapter for Feature 011 validation-error behavior."""

from collections.abc import Callable

from fastapi import FastAPI

from sciscope.api.app import create_app
from sciscope.api.http_models import QuestionRequest


def create_validation_app(*, request_id_factory: Callable[[], str]) -> FastAPI:
    """Create an app with a route used only to trigger request validation.

    Args:
        request_id_factory: Supplies deterministic error-envelope IDs in tests.

    Returns:
        An application with no production question route.
    """
    app = create_app(
        retrieval=object(),
        provider=object(),
        request_id_factory=request_id_factory,
    )

    @app.post("/__test__/validation")
    async def validate_request(_: QuestionRequest) -> None:
        raise AssertionError(
            "The validation adapter must receive invalid input"
        )

    return app
