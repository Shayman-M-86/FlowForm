---
title: AWS CDK staging plan
aliases: ["AWS CDK staging plan"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-07-27
tags: [infrastructure, configuration, ci-cd]
related_code:
  - "../../../infra/deployment/aws/cdk/"
  - "../../../infra/deployment/bootstrap/"
  - "../../../infra/containers/"
  - "../../../infra/images/"
  - "../../../.github/workflows/"
related_docs:
  - "Engineering planning"
  - "ADR 0001: AWS staging infrastructure target"
---

# AWS CDK staging plan

> Working proposal, not current architecture or deployment truth.

This plan sequences a first empty-data AWS staging environment around the
boundaries in [[0001-aws-staging-infrastructure-target|ADR 0001]]. It covers
CDK resources, host bootstrap, runtime configuration, release ordering, and
acceptance evidence. It does not claim production availability or a retained
data cutover.

The plan's phases are: accept the target; establish registry/security
contracts; finish network and data resources; make compute self-converging;
complete runtime configuration; integrate frontend/DNS; add observability and
recovery; and build the staging delivery pipeline. Each phase requires source
review and deployed evidence before being considered complete.

```text
accept target
    |
registry + security contracts
    |
network + data resources
    |
self-converging compute
    |
runtime configuration
    |
frontend + DNS
    |
observability + recovery
    |
staging delivery pipeline
```

Its baseline and completion claims have not been checked against the current
implementation. Consult linked source paths and current infrastructure
knowledge before making implementation decisions.

## Related documents

- [[planning-index|Engineering planning]]
- [[0001-aws-staging-infrastructure-target|ADR 0001: AWS staging infrastructure target]]
