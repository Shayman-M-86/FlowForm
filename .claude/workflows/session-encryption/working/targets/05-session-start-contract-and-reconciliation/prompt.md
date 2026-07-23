# Pass 05: Session-Start Contract and Reconciliation

Read `.claude/workflows/session-encryption/working/targets/05-session-start-contract-and-reconciliation/spec.md` in full before writing any code.

Dependency check: confirm `.claude/workflows/session-encryption/working/pass-reports/04-session-start.md` exists. If not, stop.

This pass tightens the session-start contract before answer-save and session-loader work begins.

Files likely to modify:

- `docs/session-encryption/01-service-boundary.md`
- `docs/session-encryption/06-failure-and-logging-rules.md`
- `backend/app/services/public_submissions/core/session_starter.py`
- `backend/app/schema/api/responses/submission_sessions.py`
- session-start contract tests and E2E tests that currently expect `survey_schema`

Pass-specific constraints:

- Do not expose the browser resume token unless the core session and response envelope both commit.
- Explicitly handle the response-DB-committed/core-DB-failed session-start partial.
- Remove survey schema from session-start responses; schema delivery belongs to discovery/link-resolution flows.
- Fix misleading test/report language around rollback versus abandoned-session behavior.

{{context: context/code-conventions.md}}

{{context: context/logging-rules.md}}

{{context: context/validation-ladder.md}}

{{context: context/testing-patterns.md}}

After implementing, run: `bash backend/scripts/run-tests.sh --ai -k "session_start or submission_session"`

{{context: context/pass-report-template.md}}
