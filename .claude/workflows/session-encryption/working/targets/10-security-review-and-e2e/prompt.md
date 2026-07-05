# Pass 10: Security Review and E2E

Read `.claude/workflows/session-encryption/working/targets/10-security-review-and-e2e/spec.md` in full before doing anything.

Dependency check: confirm `.claude/workflows/session-encryption/working/pass-reports/09-session-start-reconciliation-repair.md` exists and is marked complete. If not, stop.

This pass is review and validation only — no new feature code.

Step 1: Run `/security-review` on the paths in the spec. Document every finding: file, line, severity (high/medium/low), description, recommended fix.

Step 2: Run the full E2E suite: `bash backend/scripts/run-tests.sh --ai -k "submission_session"`

Step 3: List findings requiring operator decision. Do not self-approve high-severity findings.

{{context: context/logging-rules.md}}

{{context: context/pass-report-template.md}}
