from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class DocumentationHookConfigTests(unittest.TestCase):
    def test_pre_commit_runs_correlated_staged_doc_review(self) -> None:
        hook = (ROOT / ".githooks" / "pre-commit").read_text()
        config = json.loads((ROOT / "tools" / "docsys.config.json").read_text())

        self.assertIn("docsys review --staged", hook)
        self.assertEqual(config["trigger_weight"], 0.6)
        self.assertNotIn("substantial_change_file_count", config)
        self.assertNotIn("substantial_change_line_count", config)

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
            "tools/bin/agent-hook-python-quality",
        )

    def test_removed_documentation_hooks_are_not_present(self) -> None:
        hooks = ROOT / "tools/flowform_tools/docsys/hooks"
        for name in (
            "session_start_doc_suggestion.py",
            "stop_doc_impact_review.py",
            "record_doc_review.py",
        ):
            self.assertFalse((hooks / name).exists())


if __name__ == "__main__":
    unittest.main()
