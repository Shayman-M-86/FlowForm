---
title: ADR 0001: AWS staging infrastructure target
aliases: ["ADR 0001: AWS staging infrastructure target"]
document_type: decision
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-08-04
tags: [infrastructure, security, configuration, ci-cd]
related_code: []
change_triggers:
  - "../../../infra/deployment/aws/cdk/"
  - "../../../infra/deployment/bootstrap/"
  - "../../../infra/containers/"
  - "../../../infra/machine-images/"
related_docs:
  - "Engineering decisions"
  - "AWS staging runtime convergence"
  - "ADR 0002: Low-cost AWS operating model"
---

# ADR 0001: AWS staging infrastructure target

This decision records the intended first AWS staging environment. Its
original status was accepted on 2026-07-23, but this workspace copy is not an
implementation or live-deployment attestation.

The proposal preserves the rehearsal responsibility split with a public proxy
host, private application host, private PostgreSQL service containing separate
logical core/response databases, controlled proxy egress, private ECR images,
environment configuration, file-backed secrets, and bootstrap convergence.
It favours a low-cost single-host/single-AZ staging posture over production
availability.

```text
public internet
      |
      v
 public proxy host ----controlled egress----> approved external services
      |
      v
 private application host ----> private PostgreSQL service
      |                               |
      |                         core + response databases
      v
 private image/configuration/secret sources
```

Explicit exclusions include a NAT gateway, application load balancer,
orchestrator, RDS Proxy, broad paid interface-endpoint set, public application
or database access, multi-AZ capacity, and static AWS credentials. Deployment
identities are intended to use short-lived GitHub OIDC credentials and routine
host control is intended to use SSM with a recovery path.

The remaining delivery work is coordinated in
[[aws-staging-runtime-convergence|AWS staging runtime convergence]]. Re-verify
source and current infrastructure documentation before relying on these
boundaries.

The broader cost, availability, and evolution rationale is separated into
[[0002-low-cost-aws-operating-model|ADR 0002: Low-cost AWS operating model]] so
this topology decision does not become a permanent claim about which services
or capacities are appropriate.

## Related documents

- [[decisions-index|Engineering decisions]]
- [[aws-staging-runtime-convergence|AWS staging runtime convergence]]
- [[0002-low-cost-aws-operating-model|ADR 0002: Low-cost AWS operating model]]
