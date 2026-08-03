---
title: Release recovery and readiness
aliases: ["Release recovery and readiness", "Release and rollback model"]
document_type: workflow
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-08-04
tags: [infrastructure, ci-cd]
related_code: []
change_triggers:
  - "../../../.github/workflows/"
  - "../../../infra/deployment/aws/"
  - "../../../infra/machine-images/"
  - "../../../infra/containers/"
related_docs:
  - "Operations knowledge"
  - "Deployment architecture"
  - "CI/CD implementation"
  - "Database migrations"
  - "Deployment design forces"
---

# Release recovery and readiness

A release is a coordinated transition across artifacts, infrastructure,
durable data, runtime services, and user-facing applications. A successful
build or infrastructure update is only one part of that transition.

## Intended lifecycle

```text
validate change
      |
publish immutable artifacts
      |
apply compatible infrastructure and data transitions
      |
select release + converge runtime
      |
publish user-facing applications
      |
verify service behaviour
      |
record the observed outcome
```

Each stage should consume an identified output from the preceding stage. The
workflow must not silently rebuild a different artifact after validation or
report success before the running environment has been checked.

The checked-in workflows and operator commands remain authoritative for which
parts are currently automated. This page describes the lifecycle boundary; it
does not claim that the complete chain is implemented.

## Rollback boundaries

Rollback is not one operation:

- application rollback selects an earlier compatible runtime artifact;
- frontend rollback republishes an earlier compatible static artifact;
- infrastructure rollback restores a prior declared topology where the cloud
  control plane supports it;
- configuration rollback restores a known compatible value set without
  reviving revoked credentials;
- data rollback requires an explicitly designed migration or restoration path.

Destruction and recreation can be a recovery technique for disposable
topology, but destruction is not the normal rollback for retained data or key
material. A data transition can also make an otherwise simple application
rollback unsafe, so compatibility must be decided before release.

## Readiness evidence

Deployment completion should establish more than process startup. Evidence
should cover the public request path, private service dependencies, both data
boundaries, external identity and messaging contracts where relevant, and the
configured telemetry path. A result is stronger when it can be repeated after
host replacement or a second convergence.

Health endpoints, logs, traces, and deployment outputs are complementary. None
alone proves that users can complete a meaningful flow or that operators can
recover the environment.

## Recovery posture

Recovery design should identify:

- which state is disposable, reconstructable, backed up, or externally owned;
- the independent access path used when normal host management fails;
- how certificates, secrets, configuration, and release selections are
  restored;
- how backup restoration is tested rather than merely configured;
- the acceptable interruption and data-loss boundary for each environment;
- which recovery actions require explicit human review.

Operational readiness grows from rehearsed recovery and observable outcomes,
not from the number of declared resilience features.

## Related documents

- [[operations-index|Operations knowledge]]
- [[deployment-index|Deployment architecture]]
- [[ci-cd-implementation|CI/CD implementation]]
- [[database-migrations|Database migrations]]
- [[design-forces-and-evolution|Deployment design forces]]
