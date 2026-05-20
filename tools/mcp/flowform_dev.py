"""FlowForm dev MCP server.

Exposes the FlowForm backend OpenAPI spec to an MCP client (Claude Code) as a
combination of:

- Auto-generated tools for each endpoint, derived from /openapi.json.
- Custom helper tools for navigating the spec without making real HTTP calls
  (describe_schema, list_operations, find_operations).

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
    # Hide health/auth/docs — they're noise for frontend work.
    RouteMap(pattern=r"^/api/v1/health.*", mcp_type=MCPType.EXCLUDE),
    RouteMap(pattern=r"^/api/v1/auth.*", mcp_type=MCPType.EXCLUDE),
    RouteMap(pattern=r"^/openapi\.json$", mcp_type=MCPType.EXCLUDE),
    RouteMap(pattern=r"^/docs.*", mcp_type=MCPType.EXCLUDE),
    # Treat plain GETs as MCP resources so the model can browse them cheaply;
    # POST/PUT/PATCH/DELETE stay as tools (default).
    RouteMap(methods=["GET"], mcp_type=MCPType.RESOURCE_TEMPLATE),
]


mcp = FastMCP.from_openapi(
    openapi_spec=SPEC,
    client=http_client,
    name="flowform-dev",
    route_maps=route_maps,
)


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
def list_operations(tag: str | None = None) -> list[dict[str, Any]]:
    """List endpoint operations, optionally filtered to a single OpenAPI tag.

    Each entry includes method, path, operation_id, summary, and tags. Pass
    tag=None (the default) to list everything. Tags map to backend domains
    (projects, surveys, members, versions, links, submissions, etc.).
    """
    out: list[dict[str, Any]] = []
    for path, methods in SPEC.get("paths", {}).items():
        for method, op in methods.items():
            if not isinstance(op, dict):
                continue
            op_tags = op.get("tags", []) or []
            if tag is not None and tag not in op_tags:
                continue
            out.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "operation_id": op.get("operationId"),
                    "summary": op.get("summary"),
                    "tags": op_tags,
                }
            )
    return out


@mcp.tool()
def find_operations(keyword: str) -> list[dict[str, Any]]:
    """Free-text search across operation IDs, summaries, and paths.

    Case-insensitive substring match. Useful when you remember "publish"
    or "invite" but not the exact endpoint.
    """
    needle = keyword.lower()
    out: list[dict[str, Any]] = []
    for path, methods in SPEC.get("paths", {}).items():
        for method, op in methods.items():
            if not isinstance(op, dict):
                continue
            op_id = (op.get("operationId") or "").lower()
            summary = (op.get("summary") or "").lower()
            if needle in op_id or needle in summary or needle in path.lower():
                out.append(
                    {
                        "method": method.upper(),
                        "path": path,
                        "operation_id": op.get("operationId"),
                        "summary": op.get("summary"),
                        "tags": op.get("tags", []),
                    }
                )
    return out


if __name__ == "__main__":
    mcp.run()
