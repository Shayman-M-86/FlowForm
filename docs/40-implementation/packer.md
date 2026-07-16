---
title: Packer implementation
document_type: implementation
status: draft
authority: canonical
verified_against_commit: null
tags: [infrastructure]
related_code:
  - "../../infra/images/packer/"
  - "../../infra/images/common/build-steps/"
  - "../../infra/images/proxmox/"
  - "../../infra/deployment/proxmox/terraform/"
  - "../../infra/tests/images/"
related_docs:
  - "Machine image building"
  - "Deployment model"
  - "Proxmox rehearsal implementation"
  - "Infrastructure implementation"
---

# Packer implementation
Maps the current Packer and Proxmox image boundary to its implementation.

## Directory ownership
`infra/images/packer/` owns the consolidated Packer HCL: sources, variables,
locals, required plugins, and the golden build. `infra/images/common/build-steps/`
owns software and cleanup common to AWS and Proxmox builds. Platform-only guest
steps live under `infra/images/aws/build-steps/` and
`infra/images/proxmox/build-steps/`.

`infra/images/proxmox/provisioning/` owns the ordered operator entry points:
source-template preparation first, then the Packer golden-template build.
Terraform is intentionally outside this ownership boundary under
`infra/deployment/proxmox/terraform/`.

## Entry points
- `01-prepare-proxmox-source.sh` imports and generalizes the minimal AL2023
  source template.
- `02-build-proxmox-template.sh` runs the selected Packer Proxmox build.
- `source.proxmox.pkr.hcl` uses `proxmox-clone` from the source template and an
  explicit reserved SSH address.
- `build.golden.pkr.hcl` defines the shared build and platform-specific guest
  provisioners.

## Important modules
The shared build installs base packages, Docker/Compose, AWS CLI, host
configuration, and verification requirements. The Proxmox build step configures
the guest serial console. The cleanup step removes image-specific identity and
credential state before template conversion.

The source-preparation path and Packer source disable the QEMU guest agent;
AL2023 does not support it. Packer reaches its temporary clone through the
configured static build IP instead.

## Dependency direction
Packer consumes a minimal source template and produces a reusable golden
template. Terraform consumes that completed template and produces deployment
VMs. Neither layer invokes the other. Per-role cloud-init belongs to Terraform,
not to the shared Packer golden image.

## Generated versus handwritten code
Packer variable files containing real credentials and manifests are local or
generated artifacts. Terraform cloud-init payloads are rendered locally from
their maintained templates; Terraform uploads the rendered result but the
rendered files are not committed.

## Tests and validation
`infra/tests/images/validate.sh` runs Packer syntax validation and the
source-template preparation tests. Terraform configuration is validated from
`infra/deployment/proxmox/terraform/` with `terraform validate` after its
cloud-init payloads have been rendered.

The shared golden template has been built and Terraform has cloned it into the
local rehearsal. The LocalStack runtime exposed the remaining image gap:
third-party images must be preloaded in a future Proxmox-only fixture template
before the isolated LocalStack VM can become healthy.

## Related documents

- [[Machine image building]]
- [[Deployment model]]
- [[Proxmox rehearsal implementation]]
- [[Infrastructure implementation]]
