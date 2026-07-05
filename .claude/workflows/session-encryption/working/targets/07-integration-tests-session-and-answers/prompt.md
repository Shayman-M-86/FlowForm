# Pass 07: Integration Tests — Session Start and Answer Save

Read `.claude/workflows/session-encryption/working/targets/07-integration-tests-session-and-answers/spec.md` in full before writing any code.

Dependency checks:
- Confirm `backend/app/services/public_submissions/core/answer_save.py` exists (pass 06). If not, stop.
- Confirm `backend/app/services/public_submissions/core/session_loader.py` exists (pass 06). If not, stop.

This is a validation pass — write tests only, no new service code.
New test files go in `backend/tests/integration/response/`.

After running, explicitly state which response DB locator columns were inspected and confirm they contain opaque bytes — not readable UUIDs or question IDs. This is what the operator verifies.

{{context: context/testing-patterns.md}}

After writing all tests, run: `bash backend/scripts/run-tests.sh --ai -k "session_start_encryption or answer_save_encryption"`

{{context: context/pass-report-template.md}}
