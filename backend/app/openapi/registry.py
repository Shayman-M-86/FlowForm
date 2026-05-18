"""Internal OpenAPI metadata registry.

The ``@openapi_route`` decorator records route metadata in a process-local
registry. It returns the wrapped function untouched — request parsing,
validation, auth, and response handling remain owned by the existing Flask
route, ``parse()`` helper, error handlers, and services.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel

F = TypeVar("F", bound=Callable[..., Any])


@dataclass(slots=True, frozen=True)
class RouteMetadata:
    """OpenAPI metadata captured for a single route handler."""

    method: str
    path: str
    summary: str
    tags: tuple[str, ...]
    request_model: type[BaseModel] | None
    response_model: type[BaseModel] | None
    status_code: int
    description: str | None
    handler_qualname: str


_REGISTRY: list[RouteMetadata] = []


def openapi_route(
    *,
    method: str,
    path: str,
    summary: str,
    tags: Sequence[str] = (),
    request_model: type[BaseModel] | None = None,
    response_model: type[BaseModel] | None = None,
    status_code: int = 200,
    description: str | None = None,
) -> Callable[[F], F]:
    """Register OpenAPI metadata for a Flask view function.

    This decorator is documentation-only: it records metadata in the registry
    and returns the original function unchanged. It must be stacked above the
    Flask ``@bp.route(...)`` decorator so the underlying handler is what Flask
    registers.
    """

    def decorator(func: F) -> F:
        _REGISTRY.append(
            RouteMetadata(
                method=method.upper(),
                path=path,
                summary=summary,
                tags=tuple(tags),
                request_model=request_model,
                response_model=response_model,
                status_code=status_code,
                description=description,
                handler_qualname=f"{func.__module__}.{func.__qualname__}",
            )
        )
        return func

    return decorator


def get_registered_routes() -> list[RouteMetadata]:
    """Return a snapshot of all routes registered with ``@openapi_route``."""
    return list(_REGISTRY)


def clear_registry() -> None:
    """Reset the registry. Intended for tests only."""
    _REGISTRY.clear()
