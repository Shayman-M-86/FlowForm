from app.openapi.registry import RouteMetadata, get_registered_routes, openapi_route
from app.openapi.spec import build_spec, register_openapi_blueprint

__all__ = [
    "RouteMetadata",
    "build_spec",
    "get_registered_routes",
    "openapi_route",
    "register_openapi_blueprint",
    "register_openapi_cli",
]


def register_openapi_cli(*args, **kwargs):
    """Lazy re-export of :func:`app.openapi.export.register_openapi_cli`.

    The export module depends on PyYAML (a dev-only dependency). Importing
    it eagerly here would force PyYAML into production installs even
    though prod never runs the export command. Defer the import to call
    time so ``import app.openapi`` stays prod-clean.
    """
    from app.openapi.export import register_openapi_cli as _impl

    return _impl(*args, **kwargs)
