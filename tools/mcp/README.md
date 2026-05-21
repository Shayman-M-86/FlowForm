# FlowForm Dev MCP Server

An MCP server that wraps the FlowForm backend OpenAPI spec, intended for use
inside Claude Code while developing the Studio frontend.

## What you get

- **Compact custom tools** for navigating the live OpenAPI spec without
  exposing every endpoint as a separate MCP tool.
- **Endpoint discovery**:
  - `list_endpoints(tag, method, include_internal)` — list API endpoints.
  - `find_endpoints(keyword, include_internal)` — free-text search across
    operation IDs, summaries, paths, and tags.
- **Endpoint details**:
  - `describe_endpoint(operation_id, method, path, include_internal)` — inspect
    params, request body, responses, and referenced schemas.
  - `list_endpoint_errors(operation_id, method, path, include_internal)` — list
    documented non-success responses for one route.
- **Schema lookup**:
  - `describe_schema(name)` — return the JSON schema for a component.
- **Filtered surface** — health/auth/docs routes are hidden from discovery
  unless `include_internal=true`.

## Prerequisites

- The FlowForm backend running locally (defaults to `http://localhost:5000`).
- A `.env` file at `tools/mcp/.env` with your Auth0 settings:

  ```bash
  FLOWFORM_AUTH0_DOMAIN=your-tenant.eu.auth0.com
  FLOWFORM_AUTH0_CLIENT_ID=...
  FLOWFORM_AUTH0_AUDIENCE=...
  ```

  These mirror what the Studio frontend uses (drop the `VITE_` prefix). The
  Auth0 application must have the **Device Code** grant enabled
  (Applications → your app → Advanced Settings → Grant Types).

```bash
cd backend
uv run flask run     # in another terminal
```

## First launch (login)

```bash
bash tools/mcp/run.sh
```

A browser tab opens to Auth0 — log in once. The CLI polls until you finish,
then caches the access + refresh tokens at `~/.config/flowform/token.json`
(chmod 600). Subsequent launches reuse the cache and refresh silently when
the access token expires.

To force a fresh login (switch accounts, revoked session):

```bash
bash tools/mcp/run.sh login
```

To bypass Auth0 entirely (e.g. pasting a token grabbed from the browser):

```bash
FLOWFORM_DEV_TOKEN=eyJhbGc... bash tools/mcp/run.sh
```

## Wire it into Claude Code

Add an entry to your Claude Code MCP config (typically `~/.claude.json` under
the `mcpServers` key, or via `claude mcp add`):

```json
{
  "mcpServers": {
    "flowform-openapi": {
      "command": "uv",
      "args": [
        "run",
        "--with", "fastmcp",
        "--with", "httpx",
        "python",
        "/absolute/path/to/FlowForm/tools/mcp/flowform_dev.py"
      ],
      "env": {
        "FLOWFORM_API_BASE_URL": "http://localhost:5000",
        "FLOWFORM_DEV_TOKEN": "paste-token-here"
      }
    }
  }
}
```

Restart Claude Code. The `flowform-dev` server should appear in `/mcp`.

## Configuration

| Env var | Default | Purpose |
| --- | --- | --- |
| `FLOWFORM_API_BASE_URL` | `http://localhost:5000` | Backend base URL for live calls. |
| `FLOWFORM_SPEC_URL` | `{API_BASE_URL}/openapi.json` | Override if the spec lives elsewhere. |
| `FLOWFORM_AUTH0_DOMAIN` | _(required)_ | Auth0 tenant domain for device flow. |
| `FLOWFORM_AUTH0_CLIENT_ID` | _(required)_ | Auth0 application client id. |
| `FLOWFORM_AUTH0_AUDIENCE` | _(required)_ | Auth0 API audience. |
| `FLOWFORM_DEV_TOKEN` | _(unset)_ | If set, used directly and Auth0 device flow is skipped. |
| `FLOWFORM_TOKEN_PATH` | `~/.config/flowform/token.json` | Where the cached token is stored. |

## Customizing the tool surface

Edit `route_maps` in `flowform_dev.py` to hide or reshape more endpoints. See
[FastMCP's OpenAPI docs](https://gofastmcp.com/integrations/openapi) for the
full `RouteMap` API.
