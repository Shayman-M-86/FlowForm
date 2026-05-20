"""OpenAPI 3 spec builder and documentation endpoints.

The spec is generated from the metadata registered via ``@openapi_route``
combined with Pydantic v2 ``model_json_schema()`` output. Generation happens
on first request to ``/openapi.json`` and the result is cached for the
lifetime of the Flask app.

This module is documentation-only — it never participates in request
parsing, validation, or error formatting.
"""

from __future__ import annotations

import re
import threading
import tomllib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Any, get_args, get_origin

from apispec import APISpec
from flask import Blueprint, Flask, jsonify
from pydantic import BaseModel
from werkzeug.routing import Rule

from app.openapi.errors import (
    ERROR_SCHEMA,
    ERROR_SCHEMA_NAME,
    default_error_responses,
)
from app.openapi.registry import RouteMetadata, get_registered_routes
from app.openapi.security import (
    AUTH0_OAUTH_SCHEME_NAME,
    BEARER_SCHEME_NAME,
    BEARER_SECURITY_SCHEME,
    auth0_oauth_security_scheme,
    global_security,
    optional_security,
)

# Flask uses ``<type:name>`` path converters; OpenAPI uses ``{name}``.
_FLASK_PARAM_RE = re.compile(r"<(?:(?P<conv>[^:>]+):)?(?P<name>[^>]+)>")

# Maps Flask path converters to OpenAPI parameter schemas.
_CONVERTER_SCHEMA: dict[str, dict[str, Any]] = {
    "int": {"type": "integer"},
    "float": {"type": "number"},
    "path": {"type": "string"},
    "uuid": {"type": "string", "format": "uuid"},
    "string": {"type": "string"},
}

_DEFAULT_PARAM_SCHEMA: dict[str, Any] = {"type": "string"}

# Fallback when the package metadata can't be read (e.g. running from a source
# checkout that was never installed). Keep in sync with backend/pyproject.toml
# if you ever care, but the lookup below is the primary source.
_VERSION_FALLBACK = "0.0.0"


def _backend_package_version() -> str:
    """Return the backend's declared version.

    Reads ``backend/pyproject.toml`` directly so the source of truth works
    whether the project is installed (``uv sync``) or running from a source
    checkout. Falls back to ``importlib.metadata`` when the file isn't
    findable from the current working directory, then to a static fallback.
    """
    candidates = [
        Path("pyproject.toml"),
        Path(__file__).resolve().parents[2] / "pyproject.toml",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            continue
        version = data.get("project", {}).get("version")
        if isinstance(version, str) and version:
            return version

    try:
        return _pkg_version("backend")
    except PackageNotFoundError:
        return _VERSION_FALLBACK


def _operation_id_from_qualname(handler_qualname: str) -> str:
    """Derive a camelCase operationId from the handler's qualified name.

    ``app.api.v1.projects.core.list_projects`` → ``listProjects``. The handler
    function name is the source of truth so spec consumers (codegen, MCP
    tools) get stable, unique identifiers without per-route boilerplate.
    """
    func_name = handler_qualname.rsplit(".", 1)[-1]
    parts = func_name.split("_")
    if not parts:
        return func_name
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:] if p)


_spec_cache: dict[str, Any] | None = None
_spec_lock = threading.Lock()
_AUTO_METHODS = {"HEAD", "OPTIONS"}


def _flask_path_to_openapi(path: str) -> tuple[str, list[dict[str, Any]]]:
    """Convert a Flask URL rule to an OpenAPI path plus its path parameters."""
    parameters: list[dict[str, Any]] = []

    def replace(match: re.Match[str]) -> str:
        name = match.group("name")
        conv = match.group("conv") or "string"
        schema = _CONVERTER_SCHEMA.get(conv, _DEFAULT_PARAM_SCHEMA)
        parameters.append(
            {
                "name": name,
                "in": "path",
                "required": True,
                "schema": dict(schema),
            }
        )
        return "{" + name + "}"

    openapi_path = _FLASK_PARAM_RE.sub(replace, path)
    return openapi_path, parameters


def _normalize_openapi_path(path: str) -> tuple[str, list[dict[str, Any]]]:
    """Accept either Flask-style or OpenAPI-style path templates.

    ``@openapi_route(path=...)`` may use ``{name}`` syntax directly; the
    underlying Flask route uses ``<type:name>``. Either form should produce
    the same spec output.
    """
    if "<" in path:
        return _flask_path_to_openapi(path)

    parameters: list[dict[str, Any]] = []
    for name in re.findall(r"{([^}]+)}", path):
        parameters.append(
            {
                "name": name,
                "in": "path",
                "required": True,
                "schema": dict(_DEFAULT_PARAM_SCHEMA),
            }
        )
    return path, parameters


def _rewrite_refs(node: Any) -> Any:
    """Rewrite Pydantic ``#/$defs/...`` refs to ``#/components/schemas/...``."""
    if isinstance(node, dict):
        new: dict[str, Any] = {}
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str) and value.startswith("#/$defs/"):
                new[key] = "#/components/schemas/" + value[len("#/$defs/") :]
            else:
                new[key] = _rewrite_refs(value)
        return new
    if isinstance(node, list):
        return [_rewrite_refs(item) for item in node]
    return node


def _register_model(spec: APISpec, model: type[BaseModel]) -> str:
    """Register a Pydantic model and any nested ``$defs`` with the spec.

    Returns the component name (the model's ``__name__``) so callers can build
    a ``$ref``. Safe to call repeatedly for the same model.
    """
    name = model.__name__
    existing = spec.to_dict().get("components", {}).get("schemas", {})
    if name in existing:
        return name

    schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
    defs = schema.pop("$defs", {})

    for def_name, def_schema in defs.items():
        if def_name not in existing and def_name != name:
            spec.components.schema(def_name, _rewrite_refs(def_schema))

    spec.components.schema(name, _rewrite_refs(schema))
    return name


def _schema_for_response_model(spec: APISpec, model: Any) -> dict[str, Any]:
    origin = get_origin(model)
    args = get_args(model)

    if origin is list and len(args) == 1 and isinstance(args[0], type) and issubclass(args[0], BaseModel):
        item_name = _register_model(spec, args[0])
        return {
            "type": "array",
            "items": {"$ref": f"#/components/schemas/{item_name}"},
        }

    if isinstance(model, type) and issubclass(model, BaseModel):
        response_name = _register_model(spec, model)
        return {"$ref": f"#/components/schemas/{response_name}"}

    raise TypeError(f"Unsupported OpenAPI response model: {model!r}")


def _query_parameters_for_model(model: type[BaseModel]) -> list[dict[str, Any]]:
    schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    parameters: list[dict[str, Any]] = []

    for name, property_schema in properties.items():
        parameters.append(
            {
                "name": name,
                "in": "query",
                "required": name in required,
                "schema": _rewrite_refs(property_schema),
            }
        )

    return parameters


def _build_operation(
    spec: APISpec,
    route: RouteMetadata,
    path_parameters: list[dict[str, Any]],
    security_scheme_name: str,
) -> dict[str, Any]:
    operation: dict[str, Any] = {
        "operationId": _operation_id_from_qualname(route.handler_qualname),
        "summary": route.summary,
        "tags": list(route.tags) if route.tags else [],
    }
    if route.description:
        operation["description"] = route.description
    if route.auth == "none":
        operation["security"] = []
    elif route.auth == "optional":
        operation["security"] = optional_security(security_scheme_name)
    parameters = list(path_parameters)
    if route.query_model is not None:
        parameters.extend(_query_parameters_for_model(route.query_model))
    if parameters:
        operation["parameters"] = parameters

    if route.request_model is not None and route.method in {"POST", "PUT", "PATCH", "DELETE"}:
        request_name = _register_model(spec, route.request_model)
        operation["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": f"#/components/schemas/{request_name}"},
                }
            },
        }

    responses: dict[str, Any] = {}
    if route.response_model is not None:
        responses[str(route.status_code)] = {
            "description": "Successful response.",
            "content": {
                "application/json": {
                    "schema": _schema_for_response_model(spec, route.response_model),
                }
            },
        }
    else:
        responses[str(route.status_code)] = {"description": "Successful response."}

    responses.update(default_error_responses())
    operation["responses"] = responses

    return operation


def _handler_qualname(app: Flask, rule: Rule) -> str | None:
    handler = app.view_functions.get(rule.endpoint)
    if handler is None:
        return None
    return f"{handler.__module__}.{handler.__qualname__}"


def _explicit_methods(rule: Rule) -> set[str]:
    return {method for method in rule.methods or set() if method not in _AUTO_METHODS}


def _resolve_route_locations(app: Flask, route: RouteMetadata) -> list[tuple[str, str]]:
    """Return concrete method/path pairs for a route metadata entry."""
    if route.method is not None and route.path is not None:
        return [(route.method, route.path)]

    matches: list[tuple[str, Rule]] = []
    for rule in app.url_map.iter_rules():
        if _handler_qualname(app, rule) != route.handler_qualname:
            continue
        for method in sorted(_explicit_methods(rule)):
            if route.method is None or method == route.method:
                matches.append((method, rule))

    if route.path is not None:
        matches = [(method, rule) for method, rule in matches if rule.rule == route.path]

    if not matches:
        raise RuntimeError(f"Could not derive OpenAPI route for {route.handler_qualname}.")

    if route.method is None and len(matches) > 1:
        raise RuntimeError(
            f"Could not derive a single OpenAPI method for {route.handler_qualname}; set method=... explicitly."
        )

    rules_by_path = {rule.rule for _, rule in matches}
    if route.path is None and len(rules_by_path) > 1:
        raise RuntimeError(
            f"Could not derive a single OpenAPI path for {route.handler_qualname}; set path=... explicitly."
        )

    return [(method, route.path or rule.rule) for method, rule in matches]


def build_spec(app: Flask) -> dict[str, Any]:
    """Build the OpenAPI 3 spec dictionary for the given Flask app.

    Routes registered with ``@openapi_route`` provide the operation metadata;
    the URL prefix is taken from each blueprint's registered Flask rules so
    the generated paths match what the server actually serves.
    """
    spec = APISpec(
        title=app.config.get("OPENAPI_TITLE", "FlowForm API"),
        version=app.config.get("OPENAPI_VERSION") or _backend_package_version(),
        openapi_version="3.2.0",
        info={
            "description": app.config.get(
                "OPENAPI_DESCRIPTION",
                "REST API for the FlowForm survey platform.",
            ),
        },
    )

    spec.components.schema(ERROR_SCHEMA_NAME, ERROR_SCHEMA)
    security_scheme_name = _register_security_scheme(spec, app)

    grouped: dict[str, dict[str, Any]] = {}
    for route in get_registered_routes():
        for method, path in _resolve_route_locations(app, route):
            resolved_route = RouteMetadata(
                method=method,
                path=path,
                summary=route.summary,
                tags=route.tags,
                request_model=route.request_model,
                query_model=route.query_model,
                response_model=route.response_model,
                status_code=route.status_code,
                description=route.description,
                auth=route.auth,
                handler_qualname=route.handler_qualname,
            )
            openapi_path, path_params = _normalize_openapi_path(path)
            operation = _build_operation(
                spec,
                resolved_route,
                path_params,
                security_scheme_name,
            )
            grouped.setdefault(openapi_path, {})[method.lower()] = operation

    document = spec.to_dict()
    document["servers"] = _servers_for(app)
    document["security"] = global_security(security_scheme_name)
    document["paths"] = grouped

    return document


def _register_security_scheme(spec: APISpec, app: Flask) -> str:
    """Register OAuth2 docs auth when Auth0 config is complete."""
    domain = app.config.get("AUTH0_DOMAIN")
    audience = app.config.get("AUTH0_AUDIENCE")
    client_id = app.config.get("AUTH0_CLIENT_ID")

    if isinstance(domain, str) and domain and isinstance(audience, str) and audience and client_id:
        spec.components.security_scheme(
            AUTH0_OAUTH_SCHEME_NAME,
            auth0_oauth_security_scheme(domain, audience),
        )
        return AUTH0_OAUTH_SCHEME_NAME

    spec.components.security_scheme(BEARER_SCHEME_NAME, BEARER_SECURITY_SCHEME)
    return BEARER_SCHEME_NAME


def _servers_for(app: Flask) -> list[dict[str, str]]:
    """Build the OpenAPI ``servers`` block from Flask config.

    Codegen tools and MCP clients need at least one server URL to anchor
    relative paths against. ``OPENAPI_SERVERS`` overrides with a fully
    structured list when prod/staging/etc. need to be declared; otherwise
    we fall back to a single dev entry.
    """
    configured = app.config.get("OPENAPI_SERVERS")
    if configured:
        return list(configured)

    return [
        {
            "url": app.config.get("OPENAPI_SERVER_URL", "http://localhost:5000"),
            "description": app.config.get("OPENAPI_SERVER_DESCRIPTION", "Local development"),
        }
    ]


def _get_or_build_spec(app: Flask) -> dict[str, Any]:
    global _spec_cache
    if _spec_cache is not None:
        return _spec_cache
    with _spec_lock:
        if _spec_cache is None:
            _spec_cache = build_spec(app)
    return _spec_cache


_SWAGGER_UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>{title}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        window.onload = () => {{
            window.ui = SwaggerUIBundle({{
                url: "{spec_url}",
                dom_id: "#swagger-ui",
                deepLinking: true,
                oauth2RedirectUrl: window.location.origin + "{oauth2_redirect_path}",
            }});
            window.ui.initOAuth({{
                clientId: "{oauth_client_id}",
                usePkceWithAuthorizationCodeGrant: true,
            }});
        }};
    </script>
</body>
</html>
"""


_SWAGGER_UI_OAUTH2_REDIRECT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>Swagger UI: OAuth2 Redirect</title>
</head>
<body>
    <script>
        "use strict";
        function run() {
            const oauth2 = window.opener.swaggerUIRedirectOauth2;
            const sentState = oauth2.state;
            const redirectUrl = oauth2.redirectUrl;
            const rawParams = (/code|token|error/.test(window.location.hash))
                ? window.location.hash.substring(1).replace("?", "&")
                : window.location.search.substring(1);
            const params = new URLSearchParams(rawParams);
            const query = Object.fromEntries(params.entries());
            const isValid = query.state === sentState;

            if (
                (
                    oauth2.auth.schema.get("flow") === "accessCode" ||
                    oauth2.auth.schema.get("flow") === "authorizationCode" ||
                    oauth2.auth.schema.get("flow") === "authorization_code"
                ) &&
                !oauth2.auth.code
            ) {
                if (!isValid) {
                    oauth2.errCb({
                        authId: oauth2.auth.name,
                        source: "auth",
                        level: "warning",
                        message: "Authorization may be unsafe; the returned state did not match.",
                    });
                }
                if (query.code) {
                    delete oauth2.state;
                    oauth2.auth.code = query.code;
                    oauth2.callback({ auth: oauth2.auth, redirectUrl });
                } else {
                    oauth2.errCb({
                        authId: oauth2.auth.name,
                        source: "auth",
                        level: "error",
                        message: query.error
                            ? `[${query.error}]: ${query.error_description || "no authorization code received."}`
                            : "[Authorization failed]: no authorization code received from the server.",
                    });
                }
            } else {
                oauth2.callback({ auth: oauth2.auth, token: query, isValid, redirectUrl });
            }
            window.close();
        }

        if (document.readyState !== "loading") {
            run();
        } else {
            document.addEventListener("DOMContentLoaded", run);
        }
    </script>
</body>
</html>
"""


def register_openapi_blueprint(
    app: Flask,
    *,
    spec_path: str = "/openapi.json",
    docs_path: str = "/api/v1/docs",
    oauth2_redirect_path: str = "/api/v1/docs/oauth2-redirect",
) -> None:
    """Mount ``/openapi.json``, versioned docs, and the OAuth callback on the app.

    These endpoints are unauthenticated by design — they expose the API
    surface for internal developer tooling.
    """
    bp = Blueprint("openapi", __name__)

    @bp.route(spec_path, methods=["GET"])
    def openapi_json():
        return jsonify(_get_or_build_spec(app))

    @bp.route(docs_path, methods=["GET"])
    def swagger_ui():
        html = _SWAGGER_UI_HTML.format(
            title=app.config.get("OPENAPI_TITLE", "FlowForm API"),
            spec_url=spec_path,
            oauth_client_id=app.config.get("AUTH0_CLIENT_ID") or "",
            oauth2_redirect_path=oauth2_redirect_path,
        )
        return html, 200, {"Content-Type": "text/html; charset=utf-8"}

    @bp.route(oauth2_redirect_path, methods=["GET"])
    def swagger_ui_oauth2_redirect():
        return _SWAGGER_UI_OAUTH2_REDIRECT_HTML, 200, {"Content-Type": "text/html; charset=utf-8"}

    app.register_blueprint(bp)
