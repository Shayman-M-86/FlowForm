---
title: AWS staging planning history
aliases: ["AWS staging planning history"]
document_type: historical-plan
status: draft
authority: historical
verified_evidence_digest: null
last_edited: 2026-07-30
tags: [infrastructure, configuration]
related_code: []
change_triggers:
  - "../../../../infra/deployment/aws/"
  - "../../../../infra/machine-images/"
related_docs:
  - "Completed workspace material"
  - "AWS staging runtime convergence"
---

# AWS staging planning history

This summary replaces a set of completed, superseded, and paused AWS planning
notes. It is historical context only; source, tests, operations tooling, and
live AWS inspection determine the current state.

The plans established a low-cost staging target with separated public proxy,
private application, and private database responsibilities. They also recorded
the intended use of promoted images and releases, controlled private-host
egress, short-lived deployment identities, and separate core and response data
boundaries.

Implementation history shows the AWS deployment evolved from a broad staging
stack plan into separate role-host stacks, a baseline database bootstrap path,
and later runtime and observability improvements. The foundation was treated as
substantially implemented, while service convergence, public TLS, application
host management, IAM database proof, recovery access, remote telemetry, and
safe replacement remained open.

Earlier image-reorganization notes are retained only through this summary.
Current machine-image ownership is documented from the implementation; this
historical plan must not be used to reconstruct an obsolete layout.

## Related documents

- [[completed-index|Completed workspace material]]
- [[aws-staging-runtime-convergence|AWS staging runtime convergence]]
