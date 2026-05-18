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
from typing import Any

from apispec import APISpec
from flask import Blueprint, Flask, jsonify
from pydantic import BaseModel

from app.openapi.errors import (
    ERROR_SCHEMA,
    ERROR_SCHEMA_NAME,
    default_error_responses,
)
from app.openapi.registry import RouteMetadata, get_registered_routes
from app.openapi.security import (
    BEARER_SCHEME_NAME,
    BEARER_SECURITY_SCHEME,
    global_security,
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

_spec_cache: dict[str, Any] | None = None
_spec_lock = threading.Lock()


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


def _build_operation(
    spec: APISpec, route: RouteMetadata, path_parameters: list[dict[str, Any]]
) -> dict[str, Any]:
    operation: dict[str, Any] = {
        "summary": route.summary,
        "tags": list(route.tags) if route.tags else [],
    }
    if route.description:
        operation["description"] = route.description
    if path_parameters:
        operation["parameters"] = path_parameters

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
        response_name = _register_model(spec, route.response_model)
        responses[str(route.status_code)] = {
            "description": "Successful response.",
            "content": {
                "application/json": {
                    "schema": {"$ref": f"#/components/schemas/{response_name}"},
                }
            },
        }
    else:
        responses[str(route.status_code)] = {"description": "Successful response."}

    responses.update(default_error_responses())
    operation["responses"] = responses

    return operation


def build_spec(app: Flask) -> dict[str, Any]:
    """Build the OpenAPI 3 spec dictionary for the given Flask app.

    Routes registered with ``@openapi_route`` provide the operation metadata;
    the URL prefix is taken from each blueprint's registered Flask rules so
    the generated paths match what the server actually serves.
    """
    spec = APISpec(
        title=app.config.get("OPENAPI_TITLE", "FlowForm API"),
        version=app.config.get("OPENAPI_VERSION", "1.0.0"),
        openapi_version="3.2.0",
        info={
            "description": app.config.get(
                "OPENAPI_DESCRIPTION",
                "REST API for the FlowForm survey platform.",
            ),
        },
    )

    spec.components.schema(ERROR_SCHEMA_NAME, ERROR_SCHEMA)
    spec.components.security_scheme(BEARER_SCHEME_NAME, BEARER_SECURITY_SCHEME)

    grouped: dict[str, dict[str, Any]] = {}
    for route in get_registered_routes():
        openapi_path, path_params = _normalize_openapi_path(route.path)
        operation = _build_operation(spec, route, path_params)
        grouped.setdefault(openapi_path, {})[route.method.lower()] = operation

    document = spec.to_dict()
    document["security"] = global_security()
    document["paths"] = grouped

    return document


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
            }});
        }};
    </script>
</body>
</html>
"""


def register_openapi_blueprint(
    app: Flask,
    *,
    spec_path: str = "/openapi.json",
    docs_path: str = "/docs",
) -> None:
    """Mount ``/openapi.json`` and ``/docs`` on the Flask app.

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
        )
        return html, 200, {"Content-Type": "text/html; charset=utf-8"}

    app.register_blueprint(bp)
