---
title: Machine images
aliases: ["Machine images", "Machine image building", "Packer implementation"]
document_type: architecture
status: verified
authority: canonical
verified_evidence_digest: sha256:56c64cf6882b96e9b38bf06a0c155eced5814033e9477a86a5f2bdeeb49cda8e
last_edited: 2026-08-04
tags: [infrastructure]
related_code:
  - "../../../../infra/machine-images/README.md"
  - "../../../../infra/machine-images/IMAGE-CONTRACT.md"
  - "../../../../infra/machine-images/tooling/image"
  - "../../../../infra/tests/images/validate.sh"
  - "../../../../infra/contracts/runtime-hosts.json"
change_triggers:
  - "../../../../infra/machine-images/"
  - "../../../../infra/contracts/runtime-hosts.json"
  - "../../../../infra/deployment/aws/"
  - "../../../../infra/deployment/proxmox/"
related_docs: ["Infrastructure knowledge", "AWS machine images", "Proxmox machine images", "Container runtime", "Deployment architecture", "Proxmox rehearsal"]
---

# Machine images

Machine images are immutable host foundations. They are distinct from service
container images, the Compose topology that groups those services, and the
release manifest that selects container digests. Packer produces both AWS AMIs
and Proxmox templates from a common host-capability layer while retaining the
platform-specific setup each target needs.

```text
official Amazon Linux source
             |
             v
     FlowForm base capability
         /              \
        v                v
 AWS app/proxy AMIs   Proxmox golden template
                           |
                           v
                 rehearsal fixture templates
```

## Ownership model

The base layer installs the operating-system and host capabilities shared by
roles: container runtime support, platform guest integration, hardening,
runtime directories, and image verification. It deliberately excludes role
services, runtime Compose definitions, application source, container layers,
environment values, release digests, and credentials.

AWS application and proxy images extend one exact base AMI with only their own
host bootstrap, systemd unit, common runtime helpers, and role-specific Compose
definition. The opposite role's files are rejected during verification.
Proxmox uses the same base capability to create a golden rehearsal template;
fixture templates are controlled exceptions that may preload a declared set of
container layers so the isolated rehearsal can provide local dependencies.

This gives every artifact a narrow responsibility:

| Artifact | Contains | Does not establish |
| --- | --- | --- |
| Base image or golden template | Shared host capability and platform guest setup | A deployable application role or selected release |
| AWS application/proxy AMI | One role's host bootstrap and runtime assets | Environment secrets, mutable configuration, or container release digests |
| Proxmox fixture template | Golden host capability plus an explicitly declared fixture image inventory | Runtime state, credentials, role services, or a running rehearsal |
| Service container image | One service's packaged software | Host setup or environment topology |

## Artifact lifecycle

```text
build -> record manifest -> verify -> publish/select -> deploy -> converge
  |            |             |             |                         |
source      lineage       contents      identity only            release data
```

The repository exposes one machine-image operator surface for discovery,
preflight checks, builds, verification, artifact inspection, AWS publication,
and AWS pruning. Its implementation and command help own the exact invocation
syntax. The durable lifecycle is:

1. Build a base artifact from the pinned platform source.
2. Build a role artifact from an exact base, or a Proxmox fixture from the
   golden template.
3. Record identity, source revision, platform data, and parent lineage in a
   manifest or platform tags.
4. Verify contents and lineage before making an artifact selectable.
5. Publish or configure only the identity consumed by deployment.
6. Let deployment create hosts and runtime convergence select mutable release
   data separately.

On AWS, only application and proxy AMIs are deployable selections. The base
AMI is retained as lineage and cannot be published as a role image. Proxmox
deployment consumes named templates after they have been prepared and built;
there is no equivalent SSM publication step.

## Installed host contract

Role images install versioned host assets below `/opt/flowform/host`, including
shared runtime helpers and the role-specific bootstrap entry point. The role's
systemd service reads the instance context and selected release manifest at
runtime, then converges the baked Compose definition. The checked-in
[[configuration|Configuration and secrets]] and runtime-host contract own the
shape and permissions of those runtime inputs.

This split permits a new container release or configuration revision without
rebaking a host image. An image rebuild is required when the operating-system
baseline, host capability, baked bootstrap logic, systemd unit, or baked
Compose definition changes.

## Safety and verification boundary

Repository validation checks formatting, Packer initialization and validation,
role isolation, manifest and lineage handling, runtime asset placement,
publication restrictions, AWS pruning protections, Proxmox template lineage,
and fixture disk/image policy. Those checks validate definitions and tooling;
they do not build a live artifact, publish an AMI, delete an artifact, prove a
template exists on Proxmox, or show that a deployed host is healthy.

AWS retention protects published selections across all environments, AMIs used
by non-terminated instances, the two newest application and proxy builds, and
the exact base parents of protected child images. Pruning considers only
available, self-owned FlowForm images carrying the expected management tags and
requires an explicit dry-run or apply mode. The detailed AWS and Proxmox pages
describe their differing lineage and consumption models.

## Related documents

- [[infrastructure-index|Infrastructure knowledge]]
- [[aws-machine-images|AWS machine images]]
- [[proxmox-machine-images|Proxmox machine images]]
- [[containers-index|Container runtime]]
- [[deployment-index|Deployment architecture]]
- [[proxmox-index|Proxmox rehearsal]]
