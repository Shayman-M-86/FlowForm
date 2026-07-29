from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

HOOKS_DIR = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

import session_start_doc_suggestion as session_start   # type: ignore


class SessionStartHookTests(unittest.TestCase):
    def test_documentation_context_is_suggested_once_per_session(self) -> None:
        state: dict = {}

        def load_state(_session_id: str) -> dict:
            return dict(state)

        def save_state(_session_id: str, new_state: dict) -> None:
            state.clear()
            state.update(new_state)

        with (
            patch.object(
                session_start,
                "read_hook_input",
                return_value={"session_id": "test-session", "source": "startup"},
            ),
            patch.object(session_start, "load_state", side_effect=load_state),
            patch.object(session_start, "save_state", side_effect=save_state),
        ):
            first_output = io.StringIO()
            with redirect_stdout(first_output):
                self.assertEqual(session_start.main(), 0)

            second_output = io.StringIO()
            with redirect_stdout(second_output):
                self.assertEqual(session_start.main(), 0)

        self.assertIn("consider loading that context once now", first_output.getvalue())
        self.assertEqual(second_output.getvalue(), "")
        self.assertTrue(state["doc_context_suggested"])


if __name__ == "__main__":
    unittest.main()
