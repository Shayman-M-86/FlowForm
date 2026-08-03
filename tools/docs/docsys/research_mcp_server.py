#!/usr/bin/env python3
"""One-tool MCP service that launches fresh local Codex research processes."""

from __future__ import annotations

import json
import sys
from typing import Any

from .research import RESULT_SCHEMA, ResearchRequest, ResearchRuntimeError, run_research

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "flowform-research", "version": "1.0.0"}

_RUNTIME_SCHEMA = {
    "type": "object",
    "properties": {
        "provider": {"type": "string", "const": "codex"},
        "model": {"type": "string"},
        "depth": {"type": "string", "enum": ["quick", "thorough"]},
        "elapsed_ms": {"type": "integer"},
        "run_id": {"type": "string"},
        "fresh_session": {"type": "boolean", "const": True},
        "persisted": {"type": "boolean", "const": False},
    },
    "required": [
        "provider",
        "model",
        "depth",
        "elapsed_ms",
        "run_id",
        "fresh_session",
        "persisted",
    ],
    "additionalProperties": False,
}

OUTPUT_SCHEMA = {
    **RESULT_SCHEMA,
    "properties": {**RESULT_SCHEMA["properties"], "runtime": _RUNTIME_SCHEMA},
    "required": [*RESULT_SCHEMA["required"], "runtime"],
}

TOOLS = [
    {
        "name": "research",
        "description": "Answer one FlowForm question in a fresh, isolated local Codex session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "maxLength": 4000},
                "depth": {
                    "type": "string",
                    "enum": ["quick", "thorough"],
                    "default": "quick",
                },
                "model": {"type": "string", "maxLength": 80},
                "scope": {"type": "string"},
            },
            "required": ["question"],
            "additionalProperties": False,
        },
        "outputSchema": OUTPUT_SCHEMA,
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        },
    }
]


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


def _failure(code: str, message: str) -> dict:
    return _tool_result({"error": {"code": code, "message": message}}, is_error=True)


def _research(arguments: object) -> dict:
    if not isinstance(arguments, dict):
        raise ValueError("arguments must be an object")
    unknown = sorted(set(arguments) - {"question", "depth", "model", "scope"})
    if unknown:
        raise ValueError(f"unknown argument: {unknown[0]}")
    question = arguments.get("question")
    if not isinstance(question, str):
        raise ValueError("question must be a string")
    depth = arguments.get("depth", "quick")
    model = arguments.get("model")
    scope = arguments.get("scope")
    if not isinstance(depth, str):
        raise ValueError("depth must be a string")
    if model is not None and not isinstance(model, str):
        raise ValueError("model must be a string")
    if scope is not None and not isinstance(scope, str):
        raise ValueError("scope must be a string")
    return run_research(
        ResearchRequest(question=question, depth=depth, model=model, scope=scope)
    )


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
            return _result(id_, _failure("invalid_request", "params must be an object"))
        if params.get("name") != "research":
            return _result(id_, _failure("unknown_tool", "unknown tool"))
        try:
            payload = _research(params.get("arguments") or {})
        except (ValueError, ResearchRuntimeError) as exc:
            return _result(id_, _failure("research_failed", str(exc)))
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
