#!/usr/bin/env python3
"""Private MCP tool surface for isolated documentation research processes."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from typing import Any

from .contracts import FindRequest, ReadRequest, execute_find, execute_read
from .source_retrieval import read_source, search_source

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "flowform-research-tools", "version": "1.0.0"}
_READ_ONLY = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}

TOOLS = [
    {
        "name": "find",
        "description": "Find up to three relevant FlowForm documents.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "scope": {"type": "string"},
                "code_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 5,
                },
                "match": {"type": "string", "enum": ["all", "any", "phrase"]},
            },
            "additionalProperties": False,
        },
        "annotations": _READ_ONLY,
    },
    {
        "name": "read",
        "description": "Read one bounded FlowForm document or section.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "section": {"type": "string"},
                "offset": {"type": "integer", "minimum": 0},
                "max_chars": {"type": "integer", "minimum": 500, "maximum": 8000},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
        "annotations": _READ_ONLY,
    },
    {
        "name": "search_source",
        "description": "Search allowed repository source files for literal text.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "scope": {"type": "string"},
                "file_pattern": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "annotations": _READ_ONLY,
    },
    {
        "name": "read_source",
        "description": "Read one exact repository source line range.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start_line": {"type": "integer", "minimum": 1},
                "end_line": {"type": "integer", "minimum": 1},
            },
            "required": ["path", "start_line", "end_line"],
            "additionalProperties": False,
        },
        "annotations": _READ_ONLY,
    },
]


class ToolInputError(ValueError):
    """Invalid research tool input."""


def _mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ToolInputError("arguments must be an object")
    return value


def _reject_unknown(args: dict[str, Any], allowed: set[str]) -> None:
    unknown = sorted(set(args) - allowed)
    if unknown:
        raise ToolInputError(f"unknown argument: {unknown[0]}")


def _string(args: dict[str, Any], name: str, *, required: bool = False) -> str | None:
    value = args.get(name)
    if value is None and not required:
        return None
    if not isinstance(value, str) or (required and not value.strip()):
        raise ToolInputError(f"{name} must be a non-empty string")
    return value


def _integer(
    args: dict[str, Any], name: str, *, default: int, minimum: int, maximum: int
) -> int:
    value = args.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ToolInputError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ToolInputError(f"{name} must be between {minimum} and {maximum}")
    return value


def _find(raw: object) -> dict:
    args = _mapping(raw)
    _reject_unknown(args, {"query", "scope", "code_paths", "match"})
    raw_paths = args.get("code_paths", [])
    if not isinstance(raw_paths, list) or any(
        not isinstance(path, str) for path in raw_paths
    ):
        raise ToolInputError("code_paths must be an array of strings")
    if len(raw_paths) > 5:
        raise ToolInputError("code_paths must contain at most 5 files")
    return execute_find(
        FindRequest(
            query=_string(args, "query") or "",
            scope=_string(args, "scope"),
            code_paths=tuple(raw_paths),
            match=_string(args, "match") or "all",
            limit=3,
        )
    ).as_dict()


def _read(raw: object) -> dict:
    args = _mapping(raw)
    _reject_unknown(args, {"path", "section", "offset", "max_chars"})
    return execute_read(
        ReadRequest(
            path=_string(args, "path", required=True) or "",
            section=_string(args, "section"),
            include_body=True,
            offset=_integer(args, "offset", default=0, minimum=0, maximum=1_000_000),
            max_chars=_integer(
                args, "max_chars", default=4000, minimum=500, maximum=8000
            ),
        )
    ).as_dict()


def _search_source(raw: object) -> dict:
    args = _mapping(raw)
    _reject_unknown(args, {"query", "scope", "file_pattern", "limit"})
    return search_source(
        _string(args, "query", required=True) or "",
        scope=_string(args, "scope"),
        file_pattern=_string(args, "file_pattern"),
        limit=_integer(args, "limit", default=10, minimum=1, maximum=20),
    )


def _read_source(raw: object) -> dict:
    args = _mapping(raw)
    _reject_unknown(args, {"path", "start_line", "end_line"})
    return read_source(
        _string(args, "path", required=True) or "",
        start_line=_integer(
            args, "start_line", default=1, minimum=1, maximum=10_000_000
        ),
        end_line=_integer(args, "end_line", default=1, minimum=1, maximum=10_000_000),
    )


HANDLERS: dict[str, Callable[[object], dict]] = {
    "find": _find,
    "read": _read,
    "search_source": _search_source,
    "read_source": _read_source,
}


def _result(id_: object, result: object) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _tool_result(payload: dict, *, is_error: bool = False) -> dict:
    return {
        "content": [
            {"type": "text", "text": json.dumps(payload, separators=(",", ":"))}
        ],
        "structuredContent": payload,
        "isError": is_error,
    }


def handle_request(request: dict[str, Any]) -> dict | None:
    method = request.get("method")
    id_ = request.get("id")
    if method == "initialize":
        return _result(
            id_,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        )
    if method in {"notifications/initialized", "initialized"}:
        return None
    if method == "ping":
        return _result(id_, {})
    if method == "tools/list":
        return _result(id_, {"tools": TOOLS})
    if method == "tools/call":
        params = request.get("params", {})
        if not isinstance(params, dict):
            return _result(
                id_, _tool_result({"error": "params must be an object"}, is_error=True)
            )
        name = str(params.get("name") or "")
        handler = HANDLERS.get(name)
        if handler is None:
            return _result(
                id_, _tool_result({"error": f"unknown tool: {name}"}, is_error=True)
            )
        try:
            payload = handler(params.get("arguments") or {})
        except (ToolInputError, ValueError, OSError, subprocess.SubprocessError) as exc:
            return _result(id_, _tool_result({"error": str(exc)}, is_error=True))
        return _result(id_, _tool_result(payload))
    return None


def serve(stdin=None, stdout=None) -> int:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = handle_request(request)
        if response is not None:
            stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
            stdout.flush()
    return 0


def main() -> int:
    return serve()


if __name__ == "__main__":
    raise SystemExit(main())
