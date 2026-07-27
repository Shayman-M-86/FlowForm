---
title: ADR 0001: AWS staging infrastructure target
aliases: ["ADR 0001: AWS staging infrastructure target"]
document_type: decision
status: draft
authority: working
verified_against_commit: null
tags: [infrastructure, security, configuration, ci-cd]
related_code:
  - "../../../infra/deployment/aws/cdk/"
  - "../../../infra/deployment/bootstrap/"
  - "../../../infra/containers/"
  - "../../../infra/images/"
related_docs:
  - "Engineering decisions"
  - "AWS CDK staging plan"
---

# ADR 0001: AWS staging infrastructure target

This migrated decision records the intended first AWS staging environment. Its
original status was accepted on 2026-07-23, but this workspace copy is not an
implementation or live-deployment attestation.

The proposal preserves the rehearsal responsibility split with a public proxy
host, private application host, private PostgreSQL service containing separate
logical core/response databases, controlled proxy egress, private ECR images,
environment configuration, file-backed secrets, and bootstrap convergence.
It favours a low-cost single-host/single-AZ staging posture over production
availability.

Explicit exclusions include a NAT gateway, application load balancer,
orchestrator, RDS Proxy, broad paid interface-endpoint set, public application
or database access, multi-AZ capacity, and static AWS credentials. Deployment
identities are intended to use short-lived GitHub OIDC credentials and routine
host control is intended to use SSM with a recovery path.

The detailed implementation sequence is retained in
[[aws-cdk-staging-plan|AWS CDK staging plan]]. Re-verify source and current
infrastructure documentation before relying on any of these boundaries.

## Related documents

- [[decisions-index|Engineering decisions]]
- [[aws-cdk-staging-plan|AWS CDK staging plan]]
