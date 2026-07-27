---
title: Machine images
aliases: ["Machine images"]
document_type: overview
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-27
tags: [infrastructure]
related_code:
  - "../../../../infra/images/"
related_docs:
  - "Infrastructure knowledge"
  - "Machine image building"
  - "Packer implementation"
---

# Machine images

Owns the reusable operating-system image boundary. Packer builds completed AWS
AMIs and Proxmox templates; deployment tooling consumes their identifiers and
does not invoke Packer. The `image` dispatcher under `infra/images/scripts/`
is the operator entry point for preparation, builds, verification, artifacts,
and AWS publication.

```text
source image
    |
    v
shared golden build
    |
    +--> AWS AMI --------------------> SSM image identifier
    |
    +--> Proxmox golden template ----> runtime host clones
              |
              +--> LocalStack fixture template
              +--> PostgreSQL fixture template
```

The shared golden image is an Amazon Linux 2023 runtime host with Docker,
Docker Compose, AWS CLI, common host configuration, verification, and cleanup.
It excludes application code, runtime configuration, secrets, and runtime
container images. AWS and Proxmox use different source-image and disk policies;
the Proxmox LocalStack and PostgreSQL templates are separate fixture images.

## Documents

- [[machine-image-building|Machine image building]] describes operator commands,
  build order, and validation scope.
- [[packer|Packer implementation]] maps that workflow to HCL, provisioners,
  manifests, and dispatcher code.

## Related documents

- [[infrastructure-index|Infrastructure knowledge]]
- [[machine-image-building|Machine image building]]
- [[packer|Packer implementation]]
