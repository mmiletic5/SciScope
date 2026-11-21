"""FastAPI application construction for Feature 011."""

from dataclasses import dataclass

from fastapi import FastAPI


@dataclass(frozen=True, slots=True)
class AppDependencies:
    """Opaque dependencies supplied to the application composition root.

    T002 stores these values without invoking them. Later tasks define their
    concrete contracts and connect them to request handling.
    """

    retrieval: object
    provider: object


def create_app(*, retrieval: object, provider: object) -> FastAPI:
    """Create an inert FastAPI application with explicit dependencies.

    Args:
        retrieval: An opaque retrieval dependency supplied by the caller.
        provider: An opaque answer-provider dependency supplied by the caller.

    Returns:
        A FastAPI application that stores the supplied dependencies without
        starting external resources or registering question behavior.
    """
    app = FastAPI()
    app.state.dependencies = AppDependencies(
        retrieval=retrieval,
        provider=provider,
    )
    return app
