---
title: "ADR 0002: Low-cost AWS operating model"
aliases: ["ADR 0002: Low-cost AWS operating model"]
document_type: decision
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-08-04
tags: [infrastructure, security]
related_code: []
change_triggers:
  - "../../../infra/deployment/aws/"
  - "../../../infra/containers/runtime/aws/"
related_docs:
  - "Engineering decisions"
  - "ADR 0001: AWS staging infrastructure target"
  - "Deployment design forces"
  - "Release recovery and readiness"
---

# ADR 0002: Low-cost AWS operating model

## Status

Proposed. This record distils the durable choice implied by the current staging
design. It does not attest that every consequence is implemented or proven in a
live environment.

## Context

FlowForm needs a cloud environment that exercises meaningful production-like
boundaries without carrying the standing cost and maintenance surface of a
high-availability platform before usage justifies it.

The relevant cost is broader than provider charges. Managed layers can reduce
operator effort, but each additional service also adds configuration, identity,
failure, and migration boundaries. Conversely, avoiding managed layers can
shift too much recovery and diagnosis work onto a small team.

## Decision

Adopt a low-cost initial operating model with explicit ingress, application,
data, egress, and control-plane boundaries, while accepting limited redundancy
and operator-reviewed recovery. Prefer immutable artifacts, replaceable hosts,
short-lived deployment identity, private application and data roles, and
deliberate external-service contracts.

Do not add availability or managed-service layers solely to resemble a larger
platform. Add them when observed capacity, interruption tolerance, isolation
requirements, recovery evidence, or recurring operating effort demonstrates a
need.

## Consequences

- Some roles remain single points of interruption in the initial environment.
- Host convergence and replacement must be reliable enough to support the
  accepted availability posture.
- Shared account or environment foundations reduce cost but increase blast
  radius and require deliberate lifecycle controls.
- Recovery, certificate lifecycle, patching, backup restoration, and telemetry
  need evidence because redundancy does not hide failures.
- The architecture must retain a path toward stronger isolation, managed
  connectivity, and additional capacity without requiring a product redesign.

## Reconsideration signals

Revisit this decision when recovery objectives tighten, operator burden becomes
recurring, isolation requirements grow, sustained capacity pressure appears,
or the cost of an interruption materially exceeds the savings of the current
shape.

## Related documents

- [[decisions-index|Engineering decisions]]
- [[0001-aws-staging-infrastructure-target|ADR 0001: AWS staging infrastructure target]]
- [[design-forces-and-evolution|Deployment design forces]]
- [[release-recovery-and-readiness|Release recovery and readiness]]
