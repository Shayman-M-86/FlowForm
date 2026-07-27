---
title: Image script consolidation plan
aliases: ["Image script consolidation plan"]
document_type: completed-plan
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-07-27
tags: [infrastructure, tooling]
related_code:
  - "../../../../infra/images/"
  - "../../../../infra/tests/images/"
related_docs: ["Completed workspace material"]
---

# Image script consolidation plan

This completed-plan snapshot proposed consolidating image operations behind a
single dispatcher and shared libraries while preserving Packer, Proxmox, and AWS
safety boundaries. It called for preflight-before-mutation, explicit apply and
replace operations, safe handling of local source configuration, and mock-based
tests for command routing.

Its phases covered contract tests, a dispatcher/common library, migration of
build and mutation commands, legacy-entry-point cutover, and documentation.
The plan is retained for its rationale and safety ideas only. Current script
names, supported commands, and completion state must be verified from
`infra/images/`, tests, and current Project Knowledge.

## Related documents

- [[completed-index|Completed workspace material]]
