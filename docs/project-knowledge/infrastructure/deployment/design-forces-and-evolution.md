---
title: Deployment design forces
aliases: ["Deployment design forces"]
document_type: architecture
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-08-04
tags: [infrastructure, security]
related_code: []
change_triggers:
  - "../../../../infra/deployment/aws/"
  - "../../../../infra/containers/runtime/aws/"
  - "../../../../infra/machine-images/"
related_docs:
  - "Deployment architecture"
  - "Infrastructure knowledge"
  - "External platform boundaries"
  - "Release recovery and readiness"
  - "ADR 0002: Low-cost AWS operating model"
---

# Deployment design forces

FlowForm's deployment shape balances isolation, recoverability, operating
effort, and cost. These forces explain why a small environment may deliberately
use fewer managed layers than a high-availability platform while retaining
clear boundaries between ingress, application work, data, and the deployment
control plane.

## Current design posture

The initial AWS posture favours a low standing cost and a small operational
surface. Public ingress is separated from private application and data roles,
outbound application access is constrained, and deployment identities use
short-lived authority. The trade is reduced redundancy and more responsibility
for host convergence and recovery.

This is an explicit operating choice, not proof that the least expensive shape
is always preferable. Cost includes operator time, diagnosis burden, recovery
complexity, and the consequences of an outage as well as the cloud bill.

```text
lower standing cost
       |
       +--> fewer managed layers
       +--> less idle redundancy
       `--> more explicit operating responsibility

growth or repeated operational pain
       |
       `--> buy back simplicity, capacity, or availability
```

## Environment lifecycle

An environment combines topology, selected artifacts, configuration, durable
state, and external dependencies. Those parts have different lifecycles:

- topology can be recreated without recreating retained data;
- artifacts can be promoted or rolled back without changing the topology;
- hosts should converge from known inputs rather than depend on manual repair;
- configuration and secrets require controlled seeding and rotation;
- external services may remain available even when FlowForm infrastructure is
  rebuilt;
- environment health requires live evidence after deployment.

Development, rehearsal, staging, and production do not form a simple size
ladder. Each has a different purpose, trust boundary, persistence expectation,
and acceptable interruption model. Shared infrastructure reduces cost but
increases the blast radius of lifecycle and access decisions.

## Evolution triggers

Revisit the deployment shape when observed conditions justify it. Useful
signals include:

- recurring effort caused by constrained network or management paths;
- recovery time exceeding the environment's acceptable interruption window;
- a single role becoming a material availability bottleneck;
- capacity or connection pressure becoming sustained rather than hypothetical;
- stronger isolation being required between environments or operators;
- backup, restoration, or patching duties exceeding what the current model can
  demonstrate reliably;
- growth making managed services cheaper than continued operational attention.

The response should address the measured pressure. A new managed layer is not
automatically a security or reliability improvement, and a cheaper component is
not automatically simpler to operate.

## Evidence boundary

Architecture source establishes intended controls. Cost estimates, service
limits, account configuration, and live availability can drift independently.
An evolution decision therefore needs current measurements and operational
evidence rather than relying on an older implementation sketch.

## Related documents

- [[deployment-index|Deployment architecture]]
- [[infrastructure-index|Infrastructure knowledge]]
- [[external-platform-boundaries|External platform boundaries]]
- [[release-recovery-and-readiness|Release recovery and readiness]]
- [[0002-low-cost-aws-operating-model|ADR 0002: Low-cost AWS operating model]]
