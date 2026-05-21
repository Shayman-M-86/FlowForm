"""FlowForm dev MCP server.

Exposes the FlowForm backend OpenAPI spec to an MCP client as a compact set of
custom discovery tools:

- list_endpoints and find_endpoints for route discovery.
- describe_endpoint and list_endpoint_errors for route contracts.
- describe_schema for named OpenAPI component schemas.

The spec is fetched live from a running backend. Bearer auth for outgoing
calls is acquired via the Auth0 Device Authorization Flow (see auth.py) —
first launch opens a browser for login, subsequent launches reuse the
cached token and refresh silently when it expires.

Run:

    bash tools/mcp/run.sh

Configuration via env (typically in tools/mcp/.env):

    FLOWFORM_API_BASE_URL    default: http://localhost:5000
    FLOWFORM_SPEC_URL        default: {API_BASE_URL}/openapi.json
    FLOWFORM_AUTH0_DOMAIN    Auth0 tenant domain
    FLOWFORM_AUTH0_CLIENT_ID Auth0 application client id
    FLOWFORM_AUTH0_AUDIENCE  Auth0 API audience
    FLOWFORM_DEV_TOKEN       (optional) bypass Auth0 — used as-is if set
"""

from __future__ import annotations

import os
import re
import sys
from typing import Any

import httpx
from fastmcp import FastMCP
from fastmcp.server.providers.openapi import MCPType, RouteMap

from auth import get_access_token

API_BASE_URL = os.environ.get("FLOWFORM_API_BASE_URL", "http://localhost:5000")
SPEC_URL = os.environ.get("FLOWFORM_SPEC_URL", f"{API_BASE_URL}/openapi.json")
DEV_TOKEN = os.environ.get("FLOWFORM_DEV_TOKEN") or get_access_token()


def _fetch_spec() -> dict[str, Any]:
    try:
        response = httpx.get(SPEC_URL, timeout=5.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        print(
            f"[flowform-mcp] Failed to fetch OpenAPI spec from {SPEC_URL}: {exc}",
            file=sys.stderr,
        )
        print(
            "[flowform-mcp] Start the backend with `uv run flask run` from backend/ first.",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    return response.json()


SPEC = _fetch_spec()

http_client = httpx.AsyncClient(
    base_url=API_BASE_URL,
    headers={"Authorization": f"Bearer {DEV_TOKEN}"},
    timeout=30.0,
)


route_maps = [
    # Keep generated endpoint tools/resources out of the agent-facing surface.
    # The OpenAPI spec remains available to the custom discovery tools below.
    RouteMap(pattern=r".*", mcp_type=MCPType.EXCLUDE),
]


mcp = FastMCP.from_openapi(
    openapi_spec=SPEC,
    client=http_client,
    name="flowform-openapi-mcp",
    route_maps=route_maps,
)


# --- OpenAPI helpers -----------------------------------------------------


HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}
INTERNAL_PATH_PATTERNS = (
    re.compile(r"^/api/v1/health"),
    re.compile(r"^/api/v1/auth"),
    re.compile(r"^/openapi\.json$"),
    re.compile(r"^/docs"),
)


def _is_internal_path(path: str) -> bool:
    return any(pattern.search(path) for pattern in INTERNAL_PATH_PATTERNS)


def _operation_summary(path: str, method: str, op: dict[str, Any]) -> dict[str, Any]:
    return {
        "method": method.upper(),
        "path": path,
        "operation_id": op.get("operationId"),
        "summary": op.get("summary"),
        "tags": op.get("tags", []),
    }


def _iter_operations(include_internal: bool = False) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path, methods in SPEC.get("paths", {}).items():
        if not include_internal and _is_internal_path(path):
            continue
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            if method.lower() not in HTTP_METHODS or not isinstance(op, dict):
                continue
            out.append(
                {
                    **_operation_summary(path, method, op),
                    "_operation": op,
                }
            )
    return out


def _operation_not_found(
    operation_id: str | None,
    method: str | None,
    path: str | None,
    include_internal: bool,
) -> dict[str, Any]:
    return {
        "error": "Operation not found.",
        "lookup": {
            "operation_id": operation_id,
            "method": method.upper() if method else None,
            "path": path,
        },
        "available": [
            {k: v for k, v in item.items() if k != "_operation"}
            for item in _iter_operations(include_internal=include_internal)
        ],
    }


def _find_operation(
    operation_id: str | None = None,
    method: str | None = None,
    path: str | None = None,
    include_internal: bool = False,
) -> dict[str, Any] | None:
    if not operation_id and not (method and path):
        return None

    method_normalized = method.lower() if method else None
    for item in _iter_operations(include_internal=include_internal):
        op = item["_operation"]
        if operation_id and op.get("operationId") != operation_id:
            continue
        if method_normalized and item["method"].lower() != method_normalized:
            continue
        if path and item["path"] != path:
            continue
        return item
    return None


def _schema_name_from_ref(ref: str) -> str:
    return ref.rsplit("/", 1)[-1]


def _compact_schema(schema: Any) -> Any:
    if not isinstance(schema, dict):
        return schema
    if "$ref" in schema:
        return {"schema": _schema_name_from_ref(schema["$ref"]), "$ref": schema["$ref"]}
    if "anyOf" in schema:
        return {"anyOf": [_compact_schema(item) for item in schema["anyOf"]]}
    if "oneOf" in schema:
        return {"oneOf": [_compact_schema(item) for item in schema["oneOf"]]}
    if "allOf" in schema:
        return {"allOf": [_compact_schema(item) for item in schema["allOf"]]}
    out: dict[str, Any] = {}
    for key in ("type", "format", "enum", "const", "items", "properties", "required"):
        if key in schema:
            out[key] = _compact_schema(schema[key])
    return out or schema


def _collect_schema_refs(value: Any, refs: set[str] | None = None) -> set[str]:
    if refs is None:
        refs = set()
    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str):
            refs.add(_schema_name_from_ref(ref))
        for child in value.values():
            _collect_schema_refs(child, refs)
    elif isinstance(value, list):
        for child in value:
            _collect_schema_refs(child, refs)
    return refs


def _content_schemas(content: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(content, dict):
        return {}
    out: dict[str, Any] = {}
    for content_type, media in content.items():
        if not isinstance(media, dict):
            continue
        out[content_type] = _compact_schema(media.get("schema"))
    return out


def _format_responses(op: dict[str, Any], include_success: bool) -> list[dict[str, Any]]:
    responses = op.get("responses", {})
    if not isinstance(responses, dict):
        return []

    out: list[dict[str, Any]] = []
    for status, response in responses.items():
        is_success = str(status).startswith(("2", "3"))
        if is_success != include_success:
            continue
        if not isinstance(response, dict):
            continue
        out.append(
            {
                "status": status,
                "description": response.get("description"),
                "content": _content_schemas(response.get("content")),
            }
        )
    return out


# --- Custom tools --------------------------------------------------------


@mcp.tool()
def describe_schema(name: str) -> dict[str, Any]:
    """Return the JSON schema for a named component (Pydantic model).

    Use this to inspect request/response shapes before writing a hook or
    mock. Example names: "ProjectResponse", "CreateSurveyRequest".
    """
    schemas = SPEC.get("components", {}).get("schemas", {})
    if name not in schemas:
        available = sorted(schemas.keys())
        return {
            "error": f"Schema {name!r} not found.",
            "available": available,
        }
    return schemas[name]


@mcp.tool()
def list_endpoints(
    tag: str | None = None,
    method: str | None = None,
    include_internal: bool = False,
) -> list[dict[str, Any]]:
    """List API endpoints from the OpenAPI spec.

    Filter by OpenAPI tag and/or HTTP method. Internal health/auth/docs routes
    are hidden unless include_internal=True.
    """
    method_normalized = method.lower() if method else None
    out: list[dict[str, Any]] = []
    for item in _iter_operations(include_internal=include_internal):
        if method_normalized and item["method"].lower() != method_normalized:
            continue
        if tag is not None and tag not in (item.get("tags") or []):
            continue
        out.append({k: v for k, v in item.items() if k != "_operation"})
    return out


@mcp.tool()
def find_endpoints(keyword: str, include_internal: bool = False) -> list[dict[str, Any]]:
    """Free-text search across operation IDs, summaries, paths, and tags.

    Case-insensitive substring match. Useful when you remember "publish"
    or "invite" but not the exact endpoint.
    """
    needle = keyword.lower()
    out: list[dict[str, Any]] = []
    for item in _iter_operations(include_internal=include_internal):
        searchable = " ".join(
            [
                item["path"],
                item["method"],
                item.get("operation_id") or "",
                item.get("summary") or "",
                " ".join(item.get("tags") or []),
            ]
        ).lower()
        if needle in searchable:
            out.append({k: v for k, v in item.items() if k != "_operation"})
    return out


@mcp.tool()
def describe_endpoint(
    operation_id: str | None = None,
    method: str | None = None,
    path: str | None = None,
    include_internal: bool = False,
) -> dict[str, Any]:
    """Describe one endpoint by operation_id or by method+path.

    Returns frontend-relevant contract details: parameters, request body,
    success responses, error responses, and referenced component schemas.
    """
    item = _find_operation(
        operation_id=operation_id,
        method=method,
        path=path,
        include_internal=include_internal,
    )
    if item is None:
        return _operation_not_found(operation_id, method, path, include_internal)

    op = item["_operation"]
    request_body = op.get("requestBody") if isinstance(op.get("requestBody"), dict) else None
    parameters = []
    for param in op.get("parameters", []) or []:
        if not isinstance(param, dict):
            continue
        parameters.append(
            {
                "name": param.get("name"),
                "in": param.get("in"),
                "required": param.get("required", False),
                "description": param.get("description"),
                "schema": _compact_schema(param.get("schema")),
            }
        )

    detail = {
        "endpoint": {k: v for k, v in item.items() if k != "_operation"},
        "parameters": parameters,
        "request_body": None,
        "success_responses": _format_responses(op, include_success=True),
        "error_responses": _format_responses(op, include_success=False),
        "referenced_schemas": sorted(_collect_schema_refs(op)),
    }

    if request_body is not None:
        detail["request_body"] = {
            "required": request_body.get("required", False),
            "content": _content_schemas(request_body.get("content")),
        }

    return detail


@mcp.tool()
def list_endpoint_errors(
    operation_id: str | None = None,
    method: str | None = None,
    path: str | None = None,
    include_internal: bool = False,
) -> dict[str, Any]:
    """List documented non-success responses for one endpoint.

    This reports only what the OpenAPI spec documents. If a route can raise
    extra errors that are not declared in the spec, this tool will not infer
    them.
    """
    item = _find_operation(
        operation_id=operation_id,
        method=method,
        path=path,
        include_internal=include_internal,
    )
    if item is None:
        return _operation_not_found(operation_id, method, path, include_internal)

    errors = _format_responses(item["_operation"], include_success=False)
    return {
        "endpoint": {k: v for k, v in item.items() if k != "_operation"},
        "documented_errors": errors,
        "note": None
        if errors
        else "No non-success responses are documented for this endpoint.",
    }


if __name__ == "__main__":
    mcp.run()
