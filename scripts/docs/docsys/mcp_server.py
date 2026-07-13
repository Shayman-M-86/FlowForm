#!/usr/bin/env python3
"""Model Context Protocol server for FlowForm documentation.

Exposes the deterministic ``docsys`` tools over MCP so AI agents can retrieve
concise, high-quality documentation context instead of searching the repo. This
is the preferred interface for agents.

It speaks MCP's JSON-RPC 2.0 framing over stdio directly, with no third-party
dependency, keeping the whole toolkit installable with only the standard
library. It implements the subset of MCP that tool-using clients need:
``initialize``, ``tools/list``, and ``tools/call`` (plus the ``notifications/
initialized`` acknowledgement).

Tools exposed:

    search_docs         ranked deterministic search
    get_document        one document by title or path
    get_related         neighbouring documents of a document
    get_task_context    smallest useful context for a task / changed files
    get_impacted_docs   documentation impacted by a git range
    check_freshness     freshness classification for all documents
    doc_health          documentation health snapshot

Register with a client, e.g. Claude Code:

    claude mcp add flowform-docs -- python3 scripts/docs/docsys/mcp_server.py

Every tool loads a fresh :class:`DocSet` per call so results always reflect the
current working tree; the documentation set is small enough that this is cheap.
"""
from __future__ import annotations

import json
import sys

from . import freshness as freshness_mod
from . import health as health_mod
from .context import build_context
from .impact import impact_report
from .model import DocSet
from .query import QueryEngine
from .retrieve import get_document, get_related

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "flowform-docsys", "version": "1.0.0"}

# --- tool schema declarations --------------------------------------------

TOOLS = [
    {
        "name": "search_docs",
        "description": (
            "Ranked deterministic search over FlowForm documentation. Returns "
            "the most relevant documents with scores, matched terms, and a "
            "snippet. Prefer this over reading the docs tree directly."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "search text"},
                "limit": {"type": "integer", "default": 8},
                "type": {"type": "string", "description": "filter by document_type"},
                "tag": {"type": "string", "description": "filter by tag"},
                "min_status": {
                    "type": "string",
                    "enum": ["scaffold", "draft", "verified"],
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_document",
        "description": "Retrieve one document (body + metadata) by title or path.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "identifier": {"type": "string"},
                "include_body": {"type": "boolean", "default": True},
            },
            "required": ["identifier"],
        },
    },
    {
        "name": "get_related",
        "description": "Retrieve documents linked to a document (links + backlinks).",
        "inputSchema": {
            "type": "object",
            "properties": {"identifier": {"type": "string"}},
            "required": ["identifier"],
        },
    },
    {
        "name": "get_task_context",
        "description": (
            "Assemble the smallest useful documentation context for a task and/"
            "or changed files: primary docs, neighbours, implementation "
            "locations, workflows, and open questions."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string"},
                "changed_files": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        },
    },
    {
        "name": "get_impacted_docs",
        "description": (
            "Given a git range (base/head; defaults to the working tree), list "
            "documentation that may need review, ranked by confidence, with "
            "reasons and whether each doc was already modified."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "base": {"type": "string"},
                "head": {"type": "string"},
            },
        },
    },
    {
        "name": "check_freshness",
        "description": (
            "Classify documents as current / review suggested / likely stale / "
            "unknown, using verified_against_commit and related_code."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "only": {
                    "type": "string",
                    "enum": [
                        "current",
                        "review suggested",
                        "likely stale",
                        "unknown",
                    ],
                }
            },
        },
    },
    {
        "name": "doc_health",
        "description": (
            "Documentation health snapshot: status/freshness counts, stale "
            "docs, orphans, heavily connected docs, open questions, invalid "
            "metadata, and broken links."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    },
]

# --- tool implementations ------------------------------------------------


def _tool_search(args: dict) -> dict:
    engine = QueryEngine(DocSet.load())
    results = engine.search(
        args["query"],
        limit=int(args.get("limit", 8)),
        doc_type=args.get("type"),
        tag=args.get("tag"),
        min_status=args.get("min_status"),
    )
    return {"results": [r.as_dict() for r in results]}


def _tool_get_document(args: dict) -> dict:
    doc = get_document(
        args["identifier"], include_body=args.get("include_body", True)
    )
    if doc is None:
        return {"error": f"no document matching {args['identifier']!r}"}
    return doc


def _tool_get_related(args: dict) -> dict:
    rel = get_related(args["identifier"])
    if rel is None:
        return {"error": f"no document matching {args['identifier']!r}"}
    return rel


def _tool_task_context(args: dict) -> dict:
    bundle = build_context(
        task=args.get("task", ""),
        changed_files=args.get("changed_files") or [],
    )
    return bundle.as_dict()


def _tool_impacted(args: dict) -> dict:
    return impact_report(args.get("base"), args.get("head"))


def _tool_freshness(args: dict) -> dict:
    report = freshness_mod.health_report()
    only = args.get("only")
    if only:
        report["documents"] = [
            d for d in report["documents"] if d["classification"] == only
        ]
    return report


def _tool_health(args: dict) -> dict:
    return health_mod.build_health()


HANDLERS = {
    "search_docs": _tool_search,
    "get_document": _tool_get_document,
    "get_related": _tool_get_related,
    "get_task_context": _tool_task_context,
    "get_impacted_docs": _tool_impacted,
    "check_freshness": _tool_freshness,
    "doc_health": _tool_health,
}

# --- JSON-RPC / MCP plumbing ---------------------------------------------


def _result(id_, result):
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _error(id_, code, message):
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


def handle_request(req: dict) -> dict | None:
    method = req.get("method")
    id_ = req.get("id")
    params = req.get("params") or {}

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
        return None  # notification: no response
    if method == "ping":
        return _result(id_, {})
    if method == "tools/list":
        return _result(id_, {"tools": TOOLS})
    if method == "tools/call":
        name = str(params.get("name") or "")
        args = params.get("arguments") or {}
        handler = HANDLERS.get(name)
        if handler is None:
            return _error(id_, -32602, f"unknown tool: {name}")
        try:
            payload = handler(args)
        except Exception as exc:  # surface tool errors to the client, don't crash
            return _result(
                id_,
                {
                    "content": [
                        {"type": "text", "text": f"tool error: {exc}"}
                    ],
                    "isError": True,
                },
            )
        return _result(
            id_,
            {
                "content": [
                    {"type": "text", "text": json.dumps(payload, indent=2)}
                ]
            },
        )
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
            stdout.write(json.dumps(response) + "\n")
            stdout.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    return serve()


if __name__ == "__main__":
    raise SystemExit(main())
