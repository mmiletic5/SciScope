"""FastAPI application construction for Feature 011."""

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from sciscope.api.http_models import ErrorDetail, ErrorResponse, MockMetadata
from sciscope.question_service.ids import (
    generate_request_id,
    is_valid_request_id,
)


@dataclass(frozen=True, slots=True)
class AppDependencies:
    """Opaque dependencies supplied to the application composition root.

    T002 stores these values without invoking them. Later tasks define their
    concrete contracts and connect them to request handling.
    """

    retrieval: object
    provider: object


def create_app(
    *,
    retrieval: object,
    provider: object,
    request_id_factory: Callable[[], str] = generate_request_id,
) -> FastAPI:
    """Create an inert FastAPI application with explicit dependencies.

    Args:
        retrieval: An opaque retrieval dependency supplied by the caller.
        provider: An opaque answer-provider dependency supplied by the caller.
        request_id_factory: Generates IDs for validation-error envelopes.

    Returns:
        A FastAPI application that stores the supplied dependencies without
        starting external resources or registering question behavior.
    """
    app = FastAPI()
    app.state.dependencies = AppDependencies(
        retrieval=retrieval,
        provider=provider,
    )
    install_validation_exception_handler(
        app, request_id_factory=request_id_factory
    )
    return app


def install_validation_exception_handler(
    app: FastAPI,
    *,
    request_id_factory: Callable[[], str],
) -> None:
    """Install the sanitized Feature 011 request-validation response handler.

    Args:
        app: Application receiving the exception handler.
        request_id_factory: Generates a valid replacement when no valid caller
            request ID is available.
    """

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        request_id = _valid_request_id_or_generated(
            exc.body, request_id_factory
        )
        response = ErrorResponse(
            api_version="v1",
            request_id=request_id,
            error=ErrorDetail(
                code="invalid_request",
                message=(
                    "The request does not meet this API version's validation "
                    "rules."
                ),
                retryable=False,
            ),
            metadata=MockMetadata(is_mock=True, is_test_data=True),
        )
        return JSONResponse(status_code=422, content=response.model_dump())


def _valid_request_id_or_generated(
    body: object,
    request_id_factory: Callable[[], str],
) -> str:
    """Preserve only a valid caller ID from a malformed request body."""
    if isinstance(body, dict):
        request_id = body.get("request_id")
        if isinstance(request_id, str) and is_valid_request_id(request_id):
            return request_id
    return request_id_factory()
