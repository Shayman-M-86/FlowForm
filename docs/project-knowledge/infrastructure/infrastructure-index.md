---
title: Infrastructure knowledge
aliases: ["Infrastructure knowledge"]
document_type: overview
status: verified
authority: canonical
verified_evidence_digest: sha256:2030b87b0f4063cba6ed6eccfc84dafd342a5ce37eb0899cf9c5a83f455f92e6
last_edited: 2026-07-27
tags: [infrastructure]
related_code:
  - "../../../infra/containers/"
  - "../../../infra/database/"
  - "../../../infra/deployment/"
  - "../../../infra/images/"
  - "../../../infra/tests/"
related_docs:
  - "Project Knowledge"
  - "Deployment documentation"
  - "Container runtime documentation"
  - "Machine images"
  - "Proxmox rehearsal"
  - "Local infrastructure"
  - "Secrets and configuration"
  - "Configuration implementation"
---

# Infrastructure knowledge

Owns accepted hosting, deployment, networking, image, container, and
observability knowledge across supported platforms. Checked-in definitions and
validation describe repository intent; they do not attest that an AWS or
Proxmox environment is deployed or healthy.

```text
machine-image build
        |
        v
 reusable image identifier
        |
        +---------------------+
        |                     |
        v                     v
   AWS deployment       Proxmox rehearsal
        |                     |
        +----------+----------+
                   v
          host bootstrap
                   |
                   v
       shared container runtime
                   |
          configuration + secrets
```

## Infrastructure model

FlowForm infrastructure separates reusable build artifacts from deployment
topology and runtime convergence. [[images-index|Machine images]] produces
host-image identifiers. [[deployment-index|Deployment documentation]] defines
the AWS topology and the limited publication automation currently checked in,
while [[proxmox-index|Proxmox rehearsal]] defines the isolated local rehearsal.
Neither deployment path invokes Packer while creating hosts.

Once a host exists, bootstrap consumes configuration and shared
[[containers-index|container runtime]] definitions to converge its role. The
runtime separates application and proxy responsibilities; development and
rehearsal add their own strategy overlays rather than changing that shared
contract invisibly.

Configuration crosses each layer. [[configuration|Configuration
implementation]] defines what the backend accepts, [[secrets-and-configuration|Secrets
and configuration]] explains how sensitive values reach consumers, and
[[local-infrastructure|Local infrastructure]] describes the development
composition and its state boundaries.

## Cross-cutting concerns

AWS is currently part of the deployment model rather than an independent
knowledge branch because its stacks, environment configuration, and publication
workflows form one deployment boundary. Networking is likewise platform-owned:
AWS network topology belongs with the CDK deployment model, while the isolated
bridge and relay path belong with the Proxmox rehearsal.

Observability configuration follows the runtime it serves. The Proxmox branch
explains its Alloy signal path; broader operational interpretation and response
belong with [[operations-index|Operations knowledge]]. These subjects
should become child branches only if they develop a meaningful model that
cannot be explained coherently by their current owners.

## Repository ownership

- `infra/containers/` owns buildable container images, shared runtime Compose
  definitions, and environment-specific strategy overlays.
- `infra/database/` owns maintained PostgreSQL configuration, initialization,
  schemas, and local mock data.
- `infra/images/` owns the shared Packer contract, platform builders, bounded
  fixture images, and image-build commands.
- `infra/deployment/aws/` owns CDK and AWS publication helpers;
  `infra/deployment/proxmox/` owns the local rehearsal; and
  `infra/deployment/bootstrap/` owns shared host convergence.
- `infra/tests/` contains structural validation for containers, deployment,
  and image boundaries. Passing static or synthesis checks is not live
  deployment evidence.

## Related documents

- [[project-knowledge-index|Project Knowledge]]
- [[deployment-index|Deployment documentation]]
- [[containers-index|Container runtime documentation]]
- [[images-index|Machine images]]
- [[proxmox-index|Proxmox rehearsal]]
- [[configuration|Configuration implementation]]
- [[secrets-and-configuration|Secrets and configuration]]
- [[local-infrastructure|Local infrastructure]]
