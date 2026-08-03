from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from docsys import research_mcp_server, research_tools_server


def _call(arguments: object) -> dict:
    response = research_mcp_server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "research", "arguments": arguments},
        }
    )
    assert response is not None
    return response["result"]


class ResearchMcpTests(unittest.TestCase):
    def test_public_surface_advertises_one_read_only_tool(self) -> None:
        self.assertEqual(
            [tool["name"] for tool in research_mcp_server.TOOLS],
            ["research"],
        )
        tool = research_mcp_server.TOOLS[0]
        self.assertTrue(tool["annotations"]["readOnlyHint"])
        self.assertFalse(tool["annotations"]["openWorldHint"])
        self.assertLess(
            len(json.dumps(research_mcp_server.TOOLS, separators=(",", ":")).encode()),
            4_000,
        )

    def test_research_maps_arguments_and_returns_structured_content(self) -> None:
        payload = {
            "answer": "Answer.",
            "confidence": "high",
            "basis": "documentation",
            "findings": [],
            "contradictions": [],
            "unresolved": [],
            "runtime": {},
        }
        with patch.object(
            research_mcp_server, "run_research", return_value=payload
        ) as run:
            result = _call(
                {
                    "question": "How?",
                    "depth": "thorough",
                    "model": "gpt-5.6-sol",
                    "scope": "backend",
                }
            )

        request = run.call_args.args[0]
        self.assertEqual(request.question, "How?")
        self.assertEqual(request.depth, "thorough")
        self.assertEqual(request.model, "gpt-5.6-sol")
        self.assertEqual(request.scope, "backend")
        self.assertEqual(result["structuredContent"], payload)

    def test_invalid_requests_return_one_error_shape(self) -> None:
        for result in (
            _call({}),
            _call({"question": "x", "unknown": True}),
            _call([]),
        ):
            self.assertTrue(result["isError"])
            self.assertEqual(
                set(result["structuredContent"]["error"]),
                {"code", "message"},
            )

    def test_private_surface_is_exact_and_read_only(self) -> None:
        self.assertEqual(
            [tool["name"] for tool in research_tools_server.TOOLS],
            ["find", "read", "search_source", "read_source"],
        )
        for tool in research_tools_server.TOOLS:
            self.assertTrue(tool["annotations"]["readOnlyHint"])
            self.assertFalse(tool["annotations"]["openWorldHint"])
            self.assertFalse(tool["inputSchema"]["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
