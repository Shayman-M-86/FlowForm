# Pass 09: Security Review and E2E

## Goal

This is the final validation pass. The agent runs a security review of the full
encrypted path and the full E2E test suite. The human operator reviews all
security findings and makes judgment calls before the workflow is marked done.

## Human action required

After the agent completes the security review and E2E run, the operator must:

1. Read every finding in the security review report.
2. For each finding: decide accept, fix-now, or defer-with-reason.
3. For any fix-now finding: instruct the agent to implement the fix, then re-run.
4. Sign off on the final state before closing the workflow.

## In scope for the agent

### Security review

Run `/security-review` on the following paths:

- `backend/app/crypto/`
- `backend/app/repositories/response/`
- `backend/app/services/public_submissions/`
- `backend/app/services/results.py`

Focus areas for the reviewer:

- Key material never logged, never returned in API responses, never stored in core DB
- Locators are opaque — no plaintext question IDs or session UUIDs in response DB
- Resume token never exposed before both DB commits succeed
- Admin paths always go through authorization and the decrypt service
- Deletion ordering: response DB before core DB
- Nonce uniqueness enforced at the DB level within an envelope
- AAD binding is complete — row swaps cause decryption failure
- DEK cache eviction is correct — completed/expired/abandoned sessions evict

### E2E tests

Run the full submission session E2E suite:

`bash backend/scripts/run-tests.sh --ai -k "submission_session"`

All existing E2E tests must still pass — no regressions.

### Pass report

Write a pass report to `.claude/workflows/session-encryption/working/pass-reports/09-security-review-and-e2e.md` that includes:

- Full list of security findings with severity and disposition
- E2E test results summary
- Any deferred findings with documented reasons
- Overall sign-off readiness assessment for operator review

## Done when

- [ ] Security review complete, all findings documented
- [ ] No unfixed high-severity findings
- [ ] E2E suite passes with no regressions: `bash backend/scripts/run-tests.sh --ai -k "submission_session"`
- [ ] Operator has reviewed findings and signed off

## Dependencies

Pass 08 (completion, admin, deletion) must be complete.
