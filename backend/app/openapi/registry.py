"""Internal OpenAPI metadata registry.

The ``@openapi_route`` decorator records route metadata in a process-local
registry. It returns the wrapped function untouched — request parsing,
validation, auth, and response handling remain owned by the existing Flask
route, ``parse()`` helper, error handlers, and services.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal, TypeVar

from pydantic import BaseModel

F = TypeVar("F", bound=Callable[..., Any])
ResponseModel = type[BaseModel] | Any
AuthMode = Literal["required", "optional", "none"]


@dataclass(slots=True, frozen=True)
class RouteMetadata:
    """OpenAPI metadata captured for a single route handler."""

    method: str | None
    path: str | None
    summary: str
    tags: tuple[str, ...]
    request_model: Any | None
    query_model: type[BaseModel] | None
    response_model: ResponseModel | None
    status_code: int
    description: str | None
    auth: AuthMode
    handler_qualname: str


_REGISTRY: list[RouteMetadata] = []


def openapi_route(
    *,
    summary: str,
    method: str | None = None,
    path: str | None = None,
    tags: Sequence[str] = (),
    request_model: Any | None = None,
    query_model: type[BaseModel] | None = None,
    response_model: ResponseModel | None = None,
    status_code: int = 200,
    description: str | None = None,
    auth: AuthMode = "required",
    auth_required: bool | None = None,
) -> Callable[[F], F]:
    """Register OpenAPI metadata for a Flask view function.

    This decorator is documentation-only: it records metadata in the registry
    and returns the original function unchanged. When ``method`` or ``path`` is
    omitted, the spec builder derives it from the Flask rule registered for the
    wrapped handler. Stack this above the Flask ``@bp.route(...)`` decorator so
    the registered handler can be matched later.
    """
    auth_mode: AuthMode = ("required" if auth_required else "none") if auth_required is not None else auth

    def decorator(func: F) -> F:
        _REGISTRY.append(
            RouteMetadata(
                method=method.upper() if method is not None else None,
                path=path,
                summary=summary,
                tags=tuple(tags),
                request_model=request_model,
                query_model=query_model,
                response_model=response_model,
                status_code=status_code,
                description=description,
                auth=auth_mode,
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
