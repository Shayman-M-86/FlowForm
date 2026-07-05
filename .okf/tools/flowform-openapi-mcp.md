---
type: Tool
title: flowform-openapi MCP server
description: FastMCP server that exposes the running backend's live OpenAPI spec as agent discovery tools, authenticated via Auth0 Device Authorization Flow.
resource: tools/mcp/flowform_dev.py
tags: [mcp, tooling, openapi]
timestamp: 2026-07-01T00:00:00Z
---

# Overview

`flowform_dev.py` wraps the [OpenAPI contract](/architecture/openapi-contract.md)
served by the running backend as MCP tools:

- `list_endpoints`
- `find_endpoints`
- `describe_endpoint`
- `describe_schema`
- `list_endpoint_errors`

This lets an agent navigate the current API contract without reading
backend source or risking a stale copy of a type.

# Auth

Outgoing calls are authenticated via Auth0 Device Authorization Flow,
implemented in `auth.py`. Tokens are cached AES-GCM-encrypted at
`~/.config/flowform/token.json` with silent refresh support. See also
[Authentication and authorization](/architecture/auth.md).

# Citations

[1] [.claude/rules/repomap/tools-mcp.md](../../.claude/rules/repomap/tools-mcp.md)
[2] [frontend/CLAUDE.md — Discovering the API](../../frontend/CLAUDE.md)
