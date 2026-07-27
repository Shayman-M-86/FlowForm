---
title: Deployment documentation
aliases: ["Deployment documentation"]
document_type: overview
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-27
tags: [infrastructure, ci-cd]
related_code:
  - "../../../../infra/deployment/"
  - "../../../../.github/workflows/"
related_docs: ["Infrastructure knowledge", "Deployment model", "Cloud deployment"]
---

# Deployment documentation

FlowForm deployment has two distinct concerns: declaring the environment that
should exist and publishing artifacts that an environment may consume. The CDK
application describes AWS environment shapes; the Proxmox tooling describes a
local rehearsal with comparable runtime roles. GitHub workflows currently
publish selected frontend assets and runtime images, but do not perform a full
backend deployment.

```text
declarations                  artifacts
    |                            |
    v                            v
CDK / Terraform shape      frontend / runtime images
    |                            |
    +-------------+--------------+
                  v
        configuration + secrets
                  |
                  v
           host convergence
                  |
                  v
             live verification
```

## Declared environments

The AWS model distinguishes development from full-deployment environments.
Full environments compose security, registry, networking, database,
application, frontend, and observability stacks with explicit dependencies.
Hosts consume completed machine-image identifiers and converge through shared
bootstrap contracts. A synthesized topology establishes intended resource
relationships; it does not demonstrate that those resources exist in an
account.

The local Proxmox rehearsal owns its Terraform, cloud-init, fixture, and
operator lifecycle separately. Both platforms consume machine images and
runtime definitions, but neither platform owns the process that builds those
artifacts.

## Publication and convergence

The frontend publication workflow builds and synchronizes the two frontend
applications to the staging hosting boundary. The runtime-image workflow
publishes four immutable image sources and retains a digest manifest. Neither
workflow applies CDK, promotes image digests into active runtime parameters,
runs database migrations, or restarts application hosts.

Host bootstrap and container definitions are therefore downstream consumers,
not evidence that publication completed a deployment. Configuration and secrets
must still be delivered, hosts converged, services verified, and live platform
health observed.

[[deployment-model|Deployment model]] provides the detailed environment and CDK
topology. [[cloud-deployment|Cloud deployment]] provides the exact triggers,
credentials, actions, and limits of the checked-in AWS publication workflows.

## Related documents

- [[infrastructure-index|Infrastructure knowledge]]
- [[deployment-model|Deployment model]]
- [[cloud-deployment|Cloud deployment]]
- [[images-index|Machine images]]
- [[containers-index|Container runtime documentation]]
- [[proxmox-index|Proxmox rehearsal]]
