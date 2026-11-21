"""FastAPI application construction for Feature 011."""

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from sciscope.api.http_models import ErrorDetail, ErrorResponse, MockMetadata
from sciscope.api.routes import install_question_route
from sciscope.question_service.contracts import (
    DependencyFailure,
    DependencyFailureCode,
)
from sciscope.question_service.ids import (
    generate_request_id,
    is_valid_request_id,
)
from sciscope.question_service.validation import ResponseContractFailure

_CONTROLLED_FAILURES = {
    DependencyFailureCode.RETRIEVAL_UNAVAILABLE: (
        503,
        "retrieval_unavailable",
        "The requested dependency is currently unavailable.",
        True,
    ),
    DependencyFailureCode.PROVIDER_UNAVAILABLE: (
        503,
        "provider_unavailable",
        "The requested dependency is currently unavailable.",
        True,
    ),
    DependencyFailureCode.DEPENDENCY_TIMEOUT: (
        504,
        "dependency_timeout",
        "The requested dependency timed out.",
        True,
    ),
}
_CONTRACT_FAILURE_MESSAGE = "The response could not be validated."
_INTERNAL_ERROR_MESSAGE = "An internal error occurred."


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
    """Create an offline FastAPI application with explicit dependencies.

    Args:
        retrieval: An opaque retrieval dependency supplied by the caller.
        provider: An opaque answer-provider dependency supplied by the caller.
        request_id_factory: Generates IDs for validation-error envelopes.

    Returns:
        A FastAPI application that stores the supplied dependencies, registers
        the approved question route, and starts no external resource.
    """
    app = FastAPI()
    app.state.dependencies = AppDependencies(
        retrieval=retrieval,
        provider=provider,
    )
    install_validation_exception_handler(
        app, request_id_factory=request_id_factory
    )
    install_controlled_failure_handlers(
        app, request_id_factory=request_id_factory
    )
    install_question_route(app, request_id_factory=request_id_factory)
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


def install_controlled_failure_handlers(
    app: FastAPI,
    *,
    request_id_factory: Callable[[], str],
) -> None:
    """Install Feature 011 handlers for controlled and unexpected failures.

    Args:
        app: Application receiving the exception handlers.
        request_id_factory: Generates a valid ID when handling precedes routing.
    """

    @app.exception_handler(DependencyFailure)
    async def dependency_failure_handler(
        request: Request,
        exception: DependencyFailure,
    ) -> JSONResponse:
        status_code, code, message, retryable = _CONTROLLED_FAILURES[
            exception.code
        ]
        return _error_response(
            status_code=status_code,
            code=code,
            message=message,
            retryable=retryable,
            request_id=_request_id_or_generated(request, request_id_factory),
        )

    @app.exception_handler(ResponseContractFailure)
    async def response_contract_failure_handler(
        request: Request,
        _exception: ResponseContractFailure,
    ) -> JSONResponse:
        return _error_response(
            status_code=500,
            code="response_contract_failure",
            message=_CONTRACT_FAILURE_MESSAGE,
            retryable=False,
            request_id=_request_id_or_generated(request, request_id_factory),
        )

    @app.exception_handler(Exception)
    async def unexpected_exception_handler(
        request: Request,
        _exception: Exception,
    ) -> JSONResponse:
        return _error_response(
            status_code=500,
            code="internal_error",
            message=_INTERNAL_ERROR_MESSAGE,
            retryable=False,
            request_id=_request_id_or_generated(request, request_id_factory),
        )


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    retryable: bool,
    request_id: str,
) -> JSONResponse:
    """Return one closed sanitized error envelope."""
    response = ErrorResponse(
        api_version="v1",
        request_id=request_id,
        error=ErrorDetail(
            code=code,  # type: ignore[arg-type]
            message=message,
            retryable=retryable,
        ),
        metadata=MockMetadata(is_mock=True, is_test_data=True),
    )
    return JSONResponse(status_code=status_code, content=response.model_dump())


def _request_id_or_generated(
    request: Request,
    request_id_factory: Callable[[], str],
) -> str:
    """Return a route-captured ID or generate a valid fallback ID."""
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str) and is_valid_request_id(request_id):
        return request_id
    return request_id_factory()


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
