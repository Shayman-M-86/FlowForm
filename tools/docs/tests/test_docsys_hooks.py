from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


class DocumentationHookConfigTests(unittest.TestCase):
    def test_documentation_session_start_hook_is_absent(self) -> None:
        codex = json.loads((ROOT / ".codex/hooks.json").read_text())
        claude = json.loads((ROOT / ".claude/settings.json").read_text())

        self.assertNotIn("SessionStart", codex.get("hooks", {}))
        self.assertNotIn("SessionStart", claude.get("hooks", {}))

    def test_unrelated_post_edit_hook_is_preserved(self) -> None:
        codex = json.loads((ROOT / ".codex/hooks.json").read_text())
        claude = json.loads((ROOT / ".claude/settings.json").read_text())

        self.assertEqual(
            codex["hooks"].get("PostToolUse"),
            claude["hooks"].get("PostToolUse"),
        )
        command = codex["hooks"]["PostToolUse"][0]["hooks"][0]["command"]
        self.assertEqual(
            command,
            "python3 tools/agents/hooks/post_tool_python_quality.py",
        )

    def test_removed_documentation_hooks_are_not_present(self) -> None:
        hooks = ROOT / "tools/docs/hooks"
        for name in (
            "session_start_doc_suggestion.py",
            "stop_doc_impact_review.py",
            "record_doc_review.py",
        ):
            self.assertFalse((hooks / name).exists())


if __name__ == "__main__":
    unittest.main()
