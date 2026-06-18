# Workflow: Session Encryption

Implement the encrypted session response service: answer collection, locator derivation, AES-GCM encryption, KMS key management, and session lifecycle from start to completion.

## Passes

1. crypto-helpers
2. response-repositories
3. aws-wiring-and-crypto-smoke-test
4. session-start
5. session-start-contract-and-reconciliation
6. answer-save-and-session-loader
7. integration-tests-session-and-answers
8. completion-admin-and-deletion
9. session-start-reconciliation-repair
10. security-review-and-e2e

## Setup checklist

- [ ] Copy or move source/spec docs into `source/`
- [ ] Update `working/AGENT.md` — fill in the `SOURCE_DOCS` list with paths
      relative to the workflow root (e.g. `source/core-policies.md`)
- [ ] Fill in `working/targets/01-*/spec.md` for the first pass
- [ ] Fill in `working/targets/01-*/prompt.md`
- [ ] Run: `bash .claude/workflows/session-encryption/scripts/session-start.sh`

See `working/OPERATOR.md` for full operating instructions.
