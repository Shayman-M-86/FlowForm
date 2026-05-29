"""OpenAPI 3 spec builder and documentation endpoints.

The spec is generated from the metadata registered via ``@openapi_route``
combined with Pydantic v2 ``model_json_schema()`` output. Generation happens
on first request to ``/openapi.json`` and the result is cached for the
lifetime of the Flask app.

This module is documentation-only — it never participates in request
parsing, validation, or error formatting.
"""

from __future__ import annotations

import logging
import re
import threading
import tomllib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Any, get_args, get_origin

from apispec import APISpec
from flask import Blueprint, Flask, jsonify
from pydantic import BaseModel, TypeAdapter
from werkzeug.routing import Rule

from app.openapi.errors import (
    ERROR_SCHEMA,
    ERROR_SCHEMA_NAME,
    default_error_response_components,
    default_error_response_refs,
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
from app.schema.api import limits

LOGGER = logging.getLogger(__name__)

# Flask uses ``<type:name>`` path converters; OpenAPI uses ``{name}``.
_FLASK_PARAM_RE = re.compile(r"<(?:(?P<conv>[^:>]+):)?(?P<name>[^>]+)>")


def _custom_converter_schemas() -> dict[str, dict[str, Any]]:
    """Schemas for our custom URL converters, keyed by converter name.

    Built dynamically so the spec stays in sync with the runtime:

    - Converters with ``MAX_LENGTH`` produce a string schema with
      ``maxLength``.
    - Converters with ``MIN_VALUE`` / ``MAX_VALUE`` produce an integer
      schema with ``minimum`` / ``maximum``.

    Imported lazily to avoid a circular dependency (middleware imports
    limits, which is fine; spec doesn't need to load middleware at import
    time).
    """
    from app.middleware.url_converters import URL_CONVERTERS

    schemas: dict[str, dict[str, Any]] = {}
    for name, converter_cls in URL_CONVERTERS.items():
        max_value = getattr(converter_cls, "MAX_VALUE", None)
        min_value = getattr(converter_cls, "MIN_VALUE", None)
        if isinstance(max_value, int) and isinstance(min_value, int):
            schemas[name] = {
                "type": "integer",
                "minimum": min_value,
                "maximum": max_value,
            }
            continue

        schema: dict[str, Any] = {"type": "string"}
        max_length = getattr(converter_cls, "MAX_LENGTH", None)
        if isinstance(max_length, int) and max_length > 0:
            schema["maxLength"] = max_length
        schemas[name] = schema
    return schemas


# Maps Flask path converters to OpenAPI parameter schemas. Built once on
# import — custom converters are merged in so their MAX_LENGTH lands in
# the spec.
_CONVERTER_SCHEMA: dict[str, dict[str, Any]] = {
    "int": {"type": "integer"},
    "float": {"type": "number"},
    "path": {"type": "string"},
    "uuid": {"type": "string", "format": "uuid"},
    "string": {"type": "string"},
    **_custom_converter_schemas(),
}

_DEFAULT_PARAM_SCHEMA: dict[str, Any] = {"type": "string"}

_FORMAT_STRING_MAX_LENGTHS = {
    "date": limits.DATE_VALUE_MAX,
    "date-time": limits.ISO_DATETIME_MAX,
    "email": limits.EMAIL_MAX,
    "uri": limits.URL_MAX,
    "uuid": limits.UUID_STRING_MAX,
}

_STRING_FIELD_MAX_LENGTHS = {
    "answer_family": limits.SCHEMA_ID_MAX,
    "assigned_email": limits.EMAIL_MAX,
    "auth0_user_id": limits.AUTH0_USER_ID_MAX,
    "code": limits.ERROR_CODE_MAX,
    "display_name": limits.PROJECT_NAME_MAX,
    "email": limits.EMAIL_MAX,
    "family": limits.SCHEMA_ID_MAX,
    "message": limits.ERROR_MESSAGE_MAX,
    "name": max(limits.PROJECT_NAME_MAX, limits.PUBLIC_LINK_NAME_MAX),
    "node_key": limits.SCHEMA_ID_MAX,
    "public_slug": limits.SLUG_MAX,
    "question_key": limits.SCHEMA_ID_MAX,
    "scoring_key": limits.SCHEMA_ID_MAX,
    "slug": limits.SLUG_MAX,
    "strategy": limits.SCHEMA_ID_MAX,
    "style": limits.SCHEMA_ID_MAX,
    "title": limits.SURVEY_TITLE_MAX,
    "token": limits.TOKEN_MAX,
    "token_prefix": limits.TOKEN_PREFIX_MAX,
    "type": limits.SCHEMA_ID_MAX,
    "url": limits.URL_MAX,
}

_COMPONENT_STRING_FIELD_MAX_LENGTHS = {
    "CurrentUserResponses": {
        "auth0_user_id": limits.AUTH0_USER_ID_MAX,
        "email": limits.EMAIL_MAX,
    },
    "ProjectResponses": {
        "name": limits.PROJECT_NAME_MAX,
        "slug": limits.SLUG_MAX,
    },
    "ProjectRoleResponses": {
        "description": limits.PROJECT_ROLE_DESCRIPTION_MAX,
    },
    "PublicLinkCreatedResponses": {
        "name": limits.PUBLIC_LINK_NAME_MAX,
        "token": limits.TOKEN_MAX,
        "token_prefix": limits.TOKEN_PREFIX_MAX,
    },
    "PublicLinkResponses": {
        "name": limits.PUBLIC_LINK_NAME_MAX,
        "token_prefix": limits.TOKEN_PREFIX_MAX,
    },
    "SurveyResponses": {
        "public_slug": limits.SLUG_MAX,
        "title": limits.SURVEY_TITLE_MAX,
    },
    "SurveyRoleResponses": {
        "description": limits.PROJECT_ROLE_DESCRIPTION_MAX,
    },
}

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
        except OSError, tomllib.TOMLDecodeError:
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


def _static_string_value_max_length(schema: dict[str, Any]) -> int | None:
    const_value = schema.get("const")
    if isinstance(const_value, str):
        return len(const_value)

    enum_values = schema.get("enum")
    if isinstance(enum_values, list):
        string_values = [value for value in enum_values if isinstance(value, str)]
        if string_values:
            return max(len(value) for value in string_values)

    return None


def _default_string_max_length(
    schema: dict[str, Any],
    *,
    component_name: str | None,
    property_name: str | None,
) -> int | None:
    static_max_length = _static_string_value_max_length(schema)
    if static_max_length is not None:
        return static_max_length

    schema_format = schema.get("format")
    if isinstance(schema_format, str) and schema_format in _FORMAT_STRING_MAX_LENGTHS:
        return _FORMAT_STRING_MAX_LENGTHS[schema_format]

    component_fields = _COMPONENT_STRING_FIELD_MAX_LENGTHS.get(component_name or "")
    if component_fields is not None and property_name in component_fields:
        return component_fields[property_name]

    if property_name is not None and property_name in _STRING_FIELD_MAX_LENGTHS:
        return _STRING_FIELD_MAX_LENGTHS[property_name]

    return None


def _is_string_schema(schema: dict[str, Any]) -> bool:
    enum_values = schema.get("enum")
    return (
        schema.get("type") == "string"
        or isinstance(schema.get("const"), str)
        or (isinstance(enum_values, list) and any(isinstance(value, str) for value in enum_values))
    )


def _apply_string_max_lengths(
    node: Any,
    *,
    component_name: str | None = None,
    property_name: str | None = None,
) -> None:
    """Fill OpenAPI ``maxLength`` gaps for bounded string schemas.

    Pydantic emits good ``maxLength`` values when a model field uses
    ``Field(max_length=...)``. This pass covers schema strings whose bounds
    are implicit in constants, enums, formats, or shared field names so spec
    linting matches runtime constraints without duplicating every response
    model annotation.
    """
    if isinstance(node, list):
        for item in node:
            _apply_string_max_lengths(item, component_name=component_name, property_name=property_name)
        return

    if not isinstance(node, dict):
        return

    if _is_string_schema(node) and "maxLength" not in node:
        max_length = _default_string_max_length(
            node,
            component_name=component_name,
            property_name=property_name,
        )
        if max_length is not None:
            node["maxLength"] = max_length

    properties = node.get("properties")
    if isinstance(properties, dict):
        for child_property_name, property_schema in properties.items():
            _apply_string_max_lengths(
                property_schema,
                component_name=component_name,
                property_name=child_property_name,
            )

    for key, value in node.items():
        if key == "properties":
            continue
        if isinstance(value, (dict, list)):
            _apply_string_max_lengths(value, component_name=component_name, property_name=property_name)


def _register_model(spec: APISpec, model: Any) -> str:
    """Register a Pydantic model (or ``TypeAdapter`` type) with the spec.

    Accepts either a ``BaseModel`` subclass or an ``Annotated`` type alias.
    For ``Annotated`` unions the schema title is used as the component name.

    Returns the component name so callers can build a ``$ref``. Safe to call
    repeatedly for the same model.
    """
    if isinstance(model, type) and issubclass(model, BaseModel):
        name = model.__name__
        schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
    else:
        schema = TypeAdapter(model).json_schema(ref_template="#/components/schemas/{model}")
        name = schema.get("title", repr(model))

    existing = spec.to_dict().get("components", {}).get("schemas", {})
    if name in existing:
        return name

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
    # Always emit a non-empty description so OpenAPI linters (Spectral,
    # openapi-cop, etc.) stop flagging the operation as undocumented. If
    # the @openapi_route decorator didn't pass an explicit description,
    # fall back to the summary — better than leaving the field absent.
    description = route.description or route.summary
    operation: dict[str, Any] = {
        "operationId": _operation_id_from_qualname(route.handler_qualname),
        "summary": route.summary,
        "description": description,
        "tags": list(route.tags) if route.tags else [],
    }
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
    elif route.status_code == 204:
        # 204 No Content must not declare a response body per RFC 9110.
        responses["204"] = {"description": "No content."}
    else:
        responses[str(route.status_code)] = {"description": "Successful response."}

    responses.update(default_error_response_refs())
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
        openapi_version="3.1.1",
        info={
            "description": app.config.get(
                "OPENAPI_DESCRIPTION",
                "REST API for the FlowForm survey platform.",
            ),
            "contact": {
                "name": "FlowForm Support",
                "email": "support@flow-form.com.au",
            },
        },
    )

    spec.components.schema(ERROR_SCHEMA_NAME, ERROR_SCHEMA)
    for name, response in default_error_response_components().items():
        spec.components.response(name, response)
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
    document["tags"] = _global_tags(grouped)
    document["paths"] = grouped
    component_schemas = document.get("components", {}).get("schemas", {})
    if isinstance(component_schemas, dict):
        for component_name, component_schema in component_schemas.items():
            _apply_string_max_lengths(component_schema, component_name=component_name)

    return document


def _global_tags(paths: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    """Collect every tag used on any operation into the top-level ``tags`` list.

    OpenAPI linters expect operation tags to be declared at the document
    level. We don't currently carry per-tag descriptions, so each entry is
    just ``{"name": "..."}``; descriptions can be added later if needed
    without changing this function's signature.
    """
    names: set[str] = set()
    for path_item in paths.values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            for tag in operation.get("tags") or []:
                if isinstance(tag, str):
                    names.add(tag)
    return [{"name": name} for name in sorted(names)]


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
    """Mount the OpenAPI endpoints on the Flask app.

    The caller (typically ``openapi_register_options``) is responsible for
    only invoking this in environments where the spec should be exposed —
    in prod, nothing in this module loads at all.
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

    LOGGER.info("Registered OpenAPI spec endpoint at %s", spec_path)
    LOGGER.info("Registered Swagger UI at %s", docs_path)
    LOGGER.info("Registered Swagger UI OAuth redirect at %s", oauth2_redirect_path)
