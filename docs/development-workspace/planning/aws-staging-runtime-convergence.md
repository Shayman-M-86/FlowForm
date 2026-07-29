---
title: AWS staging runtime convergence
aliases: ["AWS staging runtime convergence"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-07-30
tags: [infrastructure, configuration, security]
related_code: []
change_triggers:
  - "../../../infra/deployment/aws/"
  - "../../../infra/containers/runtime/aws/"
  - "../../../infra/machine-images/"
related_docs:
  - "Engineering planning"
  - "ADR 0001: AWS staging infrastructure target"
---

# AWS staging runtime convergence

This is the only active AWS staging work note. The declared staging foundation
exists, but infrastructure deployment is not yet evidence of a healthy public
service. Current implementation and live AWS inspection remain authoritative.

## Current objective

Prove that the proxy and application roles converge into a recoverable,
observable service that can reach its private databases and serve a healthy
public API.

## Work sequence

1. Restore normal management access to the application host, then inspect its
   bootstrap and backend failure before choosing a fix.
2. Prove the backend uses the intended IAM-authenticated database connections.
3. Correct public TLS only after confirming the certificate challenge can
   propagate and the proxy can retain the result.
4. Test the independent recovery path on a replacement host and ensure image
   cleanup leaves no temporary build credential.
5. Verify remote logs and telemetry, then repeat convergence or a planned host
   replacement to demonstrate the result is reproducible.

Host replacement remains an operator-reviewed interruption while the current
addressing design prevents ordinary create-before-delete replacement. Artifact
publication and deployment steps belong to the maintained operations tooling,
not this note.

## Completion evidence

Close this note only with evidence that both roles are manageable or
recoverable, bootstrap completes, expected containers are healthy, the backend
connects to both databases, public TLS and readiness succeed, telemetry is
queryable, and a second convergence is repeatable.
