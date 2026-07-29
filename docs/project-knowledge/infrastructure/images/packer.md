---
title: Packer implementation
aliases: ["Packer implementation"]
document_type: implementation
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-29
tags: [infrastructure]
related_code:
  - "../../../../infra/images/packer/"
  - "../../../../infra/images/scripts/"
  - "../../../../infra/images/IMAGE-CONTRACT.md"
related_docs:
  - "Machine images"
  - "Machine image building"
---

# Packer implementation

`infra/images/packer/` owns image definitions, sources, variables,
provisioners, and generated manifests. `infra/images/scripts/image` selects an
operation and assembles the needed nested HCL into a temporary flat Packer
project, because Packer loads a directory non-recursively.

```text
sources + builds + variables + provisioners
                    |
             image dispatcher
                    |
                    v
          temporary flat HCL project
                    |
                    v
               Packer build
             /              \
            v                v
     image artifact      generated manifest
```

## Build structure

- `sources/aws.pkr.hcl` defines the AWS golden source; `sources/proxmox.pkr.hcl`
  defines the Proxmox golden and fixture clone sources.
- `builds/golden.pkr.hcl` is the shared golden build. The two fixture build
  files define the LocalStack and PostgreSQL exceptions.
- `provisioners/common/` configures the common host; `provisioners/aws/` and
  `provisioners/proxmox/` apply platform-specific steps.
- `variables/` contains declarations and ignored local-value examples;
  `manifests/` contains generated artifacts used by artifact, verification, and
  publication commands.

The shared image contract requires an Amazon Linux 2023 host with Docker,
Docker Compose, AWS CLI, required directories, and cleanup. It forbids
application code, credentials, environment-specific settings, and runtime
container images in the golden image.

## Platform divergence and fixtures

AWS builds from a minimal Amazon Linux 2023 EC2 AMI and enforces an encrypted
gp3 root-volume policy. Proxmox prepares an Amazon Linux 2023 KVM QCOW2 source
and preserves its native disk size by default. The Proxmox image path uses a
configured static build address rather than QEMU guest-agent discovery.

The LocalStack and PostgreSQL fixture templates derive from the clean Proxmox
golden template. Their provisioners derive allowed container image references
from their maintained rehearsal Compose inputs and create inventory/archive
artifacts. The fixture contract excludes Compose files, runtime configuration,
secrets, TLS material, running containers, and service state.

## Dependency boundary

Packer produces reusable image artifacts. Terraform and CDK consume their
identifiers; runtime bootstrap and Compose supply environment-specific files and
start services after instance creation.

## Related documents

- [[images-index|Machine images]]
- [[machine-image-building|Machine image building]]
