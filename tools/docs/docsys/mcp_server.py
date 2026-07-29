#!/usr/bin/env python3
"""Small, read-only MCP adapter for progressive Docsys discovery."""
from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import Any

from .contracts import (
    FindRequest,
    ReadRequest,
    execute_find,
    execute_read,
)

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "flowform-docsys", "version": "2.0.0"}

_READ_ONLY = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}

_FIND_OUTPUT = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "maxItems": 5,
            "items": {
                "type": "object",
                "properties": {
                    name: {"type": "string"}
                    for name in ("path", "title", "status", "summary")
                },
                "required": ["path", "title", "status", "summary"],
                "additionalProperties": False,
            },
        },
        "total": {"type": "integer"},
        "returned": {"type": "integer", "maximum": 5},
        "truncated": {"type": "boolean"},
        "warning": {"type": "string"},
    },
    "required": ["items", "total", "returned", "truncated"],
    "additionalProperties": False,
}

_READ_OUTPUT = {
    "type": "object",
    "properties": {
        **{
            name: {"type": "string"}
            for name in ("path", "title", "status", "summary", "content")
        },
        "headings": {"type": "array", "items": {"type": "string"}},
        "truncated": {"type": "boolean"},
        "next_offset": {"type": ["integer", "null"]},
    },
    "required": [
        "path",
        "title",
        "status",
        "summary",
        "headings",
        "content",
        "truncated",
        "next_offset",
    ],
    "additionalProperties": False,
}

TOOLS = [
    {
        "name": "find",
        "description": "Find a few relevant FlowForm documents.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "scope": {"type": "string"},
                "code_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 10,
                },
                "match": {
                    "type": "string",
                    "enum": ["all", "any", "phrase"],
                    "default": "all",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "default": 3,
                },
            },
            "additionalProperties": False,
        },
        "outputSchema": _FIND_OUTPUT,
        "annotations": _READ_ONLY,
    },
    {
        "name": "read",
        "description": "Read one exact document path or section.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "section": {"type": "string"},
                "offset": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0,
                },
                "max_chars": {
                    "type": "integer",
                    "minimum": 500,
                    "maximum": 8000,
                    "default": 4000,
                },
            },
            "required": ["path"],
            "additionalProperties": False,
        },
        "outputSchema": _READ_OUTPUT,
        "annotations": _READ_ONLY,
    },
]

_FIND_KEYS = frozenset({"query", "scope", "code_paths", "match", "limit"})
_READ_KEYS = frozenset({"path", "section", "offset", "max_chars"})


class ToolInputError(ValueError):
    """An invalid MCP tool argument."""


def _require_mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ToolInputError("arguments must be an object")
    return value


def _reject_unknown(args: dict[str, Any], allowed: frozenset[str]) -> None:
    unknown = sorted(set(args) - allowed)
    if unknown:
        raise ToolInputError(f"unknown argument: {unknown[0]}")


def _optional_string(
    args: dict[str, Any], name: str, *, default: str | None = None
) -> str | None:
    value = args.get(name, default)
    if value is not None and not isinstance(value, str):
        raise ToolInputError(f"{name} must be a string")
    return value


def _integer(
    args: dict[str, Any],
    name: str,
    *,
    default: int,
    minimum: int,
    maximum: int | None = None,
) -> int:
    value = args.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ToolInputError(f"{name} must be an integer")
    if value < minimum or (maximum is not None and value > maximum):
        upper = f" and {maximum}" if maximum is not None else ""
        raise ToolInputError(f"{name} must be between {minimum}{upper}")
    return value


def _tool_find(raw_args: object) -> dict[str, Any]:
    args = _require_mapping(raw_args)
    _reject_unknown(args, _FIND_KEYS)

    query = _optional_string(args, "query", default="") or ""
    scope = _optional_string(args, "scope")
    match = _optional_string(args, "match", default="all") or "all"
    if match not in {"all", "any", "phrase"}:
        raise ToolInputError("match must be one of: all, any, phrase")

    raw_code_paths = args.get("code_paths", [])
    if not isinstance(raw_code_paths, list) or any(
        not isinstance(path, str) for path in raw_code_paths
    ):
        raise ToolInputError("code_paths must be an array of strings")
    if len(raw_code_paths) > 10:
        raise ToolInputError("code_paths must contain at most 10 files")

    request = FindRequest(
        query=query,
        scope=scope,
        code_paths=tuple(raw_code_paths),
        match=match,
        limit=_integer(args, "limit", default=3, minimum=1, maximum=5),
    )
    return execute_find(request).as_dict()


def _tool_read(raw_args: object) -> dict[str, Any]:
    args = _require_mapping(raw_args)
    _reject_unknown(args, _READ_KEYS)

    path = _optional_string(args, "path")
    if not path:
        raise ToolInputError("path is required")

    request = ReadRequest(
        path=path,
        section=_optional_string(args, "section"),
        include_body=True,
        offset=_integer(args, "offset", default=0, minimum=0),
        max_chars=_integer(
            args,
            "max_chars",
            default=4000,
            minimum=500,
            maximum=8000,
        ),
    )
    return execute_read(request).as_dict()


HANDLERS: dict[str, Callable[[object], dict[str, Any]]] = {
    "find": _tool_find,
    "read": _tool_read,
}


def _result(id_: object, result: object) -> dict[str, object]:
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _error(id_: object, code: int, message: str) -> dict[str, object]:
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


def _tool_result(
    payload: dict[str, Any], *, is_error: bool = False
) -> dict[str, object]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            }
        ],
        "structuredContent": payload,
        "isError": is_error,
    }


def _tool_failure(code: str, message: str) -> dict[str, object]:
    return _tool_result(
        {"error": {"code": code, "message": message}},
        is_error=True,
    )


def handle_request(req: dict[str, Any]) -> dict[str, object] | None:
    method = req.get("method")
    id_ = req.get("id")
    params = req.get("params", {})
    if params is None:
        params = {}

    if method == "initialize":
        return _result(
            id_,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        )
    if method in ("notifications/initialized", "initialized"):
        return None
    if method == "ping":
        return _result(id_, {})
    if method == "tools/list":
        return _result(id_, {"tools": TOOLS})
    if method == "tools/call":
        if not isinstance(params, dict):
            return _result(
                id_, _tool_failure("invalid_request", "params must be an object")
            )
        name = str(params.get("name") or "")
        handler = HANDLERS.get(name)
        if handler is None:
            return _result(
                id_, _tool_failure("unknown_tool", f"unknown tool: {name}")
            )
        try:
            arguments = params.get("arguments", {})
            if arguments is None:
                arguments = {}
            payload = handler(arguments)
        except (ToolInputError, ValueError, FileNotFoundError) as exc:
            return _result(id_, _tool_failure("invalid_request", str(exc)))
        except Exception:
            return _result(
                id_,
                _tool_failure("tool_error", "documentation request failed"),
            )
        return _result(id_, _tool_result(payload))
    if id_ is not None:
        return _error(id_, -32601, f"method not found: {method}")
    return None


def serve(stdin=None, stdout=None) -> int:
    """Run the stdio JSON-RPC loop until EOF."""
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = handle_request(req)
        if response is not None:
            stdout.write(
                json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n"
            )
            stdout.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    return serve()


if __name__ == "__main__":
    raise SystemExit(main())
