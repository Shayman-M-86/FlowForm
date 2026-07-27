---
title: Infrastructure knowledge
aliases: ["Infrastructure knowledge"]
document_type: overview
status: verified
authority: canonical
verified_against_commit: 0edae9082dc3381cc1376e8a81276bf5c7bebf88
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

## Knowledge branches

- [[deployment-index|Deployment documentation]] owns declared deployment
  topology and bounded cloud-publication workflows.
- [[containers-index|Container runtime documentation]] owns shared Compose
  boundaries and strategy overlays.
- [[images-index|Machine images]] owns Packer-built host images and their
  operator workflow.
- [[proxmox-index|Proxmox rehearsal]] owns the local rehearsal topology,
  fixtures, setup, and telemetry path.
- [[aws-index|AWS infrastructure]], [[networking-index|Infrastructure
  networking]], and [[observability-index|Infrastructure observability]] are
  reserved scaffold branches pending the human taxonomy review.

Configuration that crosses those branches is documented directly:
[[local-infrastructure|Local infrastructure]], [[secrets-and-configuration|Secrets
and configuration]], and [[configuration|Configuration implementation]].

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
