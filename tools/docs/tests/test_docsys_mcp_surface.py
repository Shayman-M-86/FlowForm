from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from docsys import mcp_server


def _call(name: str, arguments: object) -> dict:
    response = mcp_server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
    )
    assert response is not None
    return response["result"]


class McpSurfaceTests(unittest.TestCase):
    def test_advertises_only_two_small_read_only_tools(self) -> None:
        self.assertEqual([tool["name"] for tool in mcp_server.TOOLS], ["find", "read"])
        self.assertLess(
            len(
                json.dumps(
                    mcp_server.TOOLS,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode()
            ),
            2000,
        )

        for tool in mcp_server.TOOLS:
            schema = tool["inputSchema"]
            self.assertFalse(schema["additionalProperties"])
            self.assertNotIn("docs_root", schema["properties"])
            self.assertFalse(tool["outputSchema"]["additionalProperties"])
            self.assertEqual(
                tool["annotations"],
                {
                    "readOnlyHint": True,
                    "destructiveHint": False,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
            )

        find = mcp_server.TOOLS[0]["inputSchema"]["properties"]
        self.assertEqual(find["limit"]["default"], 3)
        self.assertEqual(find["limit"]["maximum"], 5)
        self.assertEqual(find["code_paths"]["maxItems"], 10)

        read = mcp_server.TOOLS[1]["inputSchema"]["properties"]
        self.assertEqual(read["max_chars"]["default"], 4000)
        self.assertEqual(read["max_chars"]["maximum"], 8000)

    def test_initialize_and_list_do_not_execute_document_operations(self) -> None:
        with patch.object(mcp_server, "execute_find") as find, patch.object(
            mcp_server, "execute_read"
        ) as read:
            initialized = mcp_server.handle_request(
                {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
            )
            listed = mcp_server.handle_request(
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
            )

        self.assertEqual(
            initialized["result"]["serverInfo"]["name"],
            "flowform-docsys",
        )
        self.assertEqual(
            [tool["name"] for tool in listed["result"]["tools"]],
            ["find", "read"],
        )
        find.assert_not_called()
        read.assert_not_called()

    def test_find_uses_the_shared_contract_and_returns_compact_structured_data(
        self,
    ) -> None:
        payload = {
            "items": [
                {
                    "path": "docs/example.md",
                    "title": "Example",
                    "status": "draft",
                    "summary": "Short.",
                }
            ],
            "total": 1,
            "returned": 1,
            "truncated": False,
        }
        with patch.object(
            mcp_server,
            "execute_find",
            return_value=SimpleNamespace(as_dict=lambda: payload),
        ) as execute:
            result = _call(
                "find",
                {
                    "query": "exact terms",
                    "scope": "docs/project-knowledge",
                    "code_paths": ["backend/app/main.py"],
                    "match": "phrase",
                    "limit": 5,
                },
            )

        request = execute.call_args.args[0]
        self.assertEqual(request.query, "exact terms")
        self.assertEqual(request.scope, "docs/project-knowledge")
        self.assertEqual(request.code_paths, ("backend/app/main.py",))
        self.assertEqual(request.match, "phrase")
        self.assertEqual(request.limit, 5)
        self.assertFalse(result["isError"])
        self.assertEqual(result["structuredContent"], payload)
        self.assertEqual(json.loads(result["content"][0]["text"]), payload)
        self.assertNotIn("\n", result["content"][0]["text"])
        self.assertLess(len(result["content"][0]["text"].encode()), 8000)

    def test_read_uses_an_exact_bounded_shared_request(self) -> None:
        payload = {
            "path": "docs/example.md",
            "title": "Example",
            "status": "draft",
            "summary": "Short.",
            "headings": ["Example"],
            "content": "bounded",
            "start_line": 20,
            "end_line": 20,
            "truncated": False,
            "next_offset": None,
        }
        with patch.object(
            mcp_server,
            "execute_read",
            return_value=SimpleNamespace(as_dict=lambda: payload),
        ) as execute:
            result = _call(
                "read",
                {
                    "path": "docs/example.md",
                    "section": "Details",
                    "offset": 25,
                    "max_chars": 8000,
                },
            )

        request = execute.call_args.args[0]
        self.assertEqual(request.path, "docs/example.md")
        self.assertEqual(request.section, "Details")
        self.assertTrue(request.include_body)
        self.assertEqual(request.offset, 25)
        self.assertEqual(request.max_chars, 8000)
        self.assertFalse(result["isError"])

    def test_invalid_and_unknown_requests_use_one_error_shape(self) -> None:
        cases = [
            _call("find", {}),
            _call("find", {"query": "x", "limit": 6}),
            _call("find", {"query": "x", "unexpected": True}),
            _call("find", []),
            _call("read", {}),
            _call("read", {"path": "docs/example.md", "max_chars": 499}),
            _call("missing", {}),
        ]

        for result in cases:
            self.assertTrue(result["isError"])
            error = result["structuredContent"]["error"]
            self.assertEqual(set(error), {"code", "message"})
            self.assertEqual(
                json.loads(result["content"][0]["text"]),
                result["structuredContent"],
            )


if __name__ == "__main__":
    unittest.main()
