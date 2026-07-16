---
title: Machine image building
document_type: workflow
status: draft
authority: canonical
verified_against_commit: null
tags: [infrastructure]
related_code:
  - "../../infra/images/packer/"
  - "../../infra/images/proxmox/provisioning/"
  - "../../infra/images/common/build-steps/"
  - "../../infra/tests/images/"
related_docs:
  - "Cloud deployment"
  - "Packer implementation"
  - "Deployment model"
  - "Proxmox rehearsal implementation"
  - "Infrastructure resources"
---

# Machine image building
Describes the current Packer workflow for the shared Amazon Linux 2023 image.
It covers image construction only; [[Deployment model|Terraform deployment]]
clones a completed Proxmox template and does not invoke Packer.

## Trigger
Run this workflow when the reusable operating-system image needs changing: for
example, an updated Amazon Linux source image, common package change, or image
hardening change. It is not a normal application or environment deployment
step.

## Preconditions
- Packer and its configured Proxmox plugin are available on the Linux/WSL build
  host.
- `infra/images/proxmox/.env` exists and identifies the Proxmox SSH host,
  pinned AL2023 KVM source, storage, source-template VMID, and bridge.
- `infra/images/packer/proxmox.auto.pkrvars.hcl` exists with Proxmox API
  credentials, node, source-template name, output VMID, and a reserved build
  address.
- The reserved build address must not respond to ping; the Packer wrapper
  rejects a build if it does.

## Ordered steps
1. Run `infra/images/proxmox/provisioning/01-prepare-proxmox-source.sh` for a
   non-mutating preflight, then rerun with `--apply` when the pinned source
   template needs creation or replacement. It imports the official AL2023 KVM
   qcow2 and produces source template `8999` in the current local rehearsal.
2. Run `infra/images/proxmox/provisioning/02-build-proxmox-template.sh`. It
   initializes Packer plugins, performs syntax validation, and runs only the
   Proxmox clone builder.
3. Packer clones the source template, applies shared and Proxmox-specific build
   steps, cleans image identity state, and converts the result to template
   `9000` in the current local rehearsal.
4. Run Terraform separately to clone a completed template into rehearsal VMs.

## Inputs and outputs
Inputs are the pinned AL2023 image configuration, Proxmox credentials, and the
Packer variable file. Outputs are a reusable Proxmox template and the generated
Packer manifest under `infra/images/common/manifests/`. The source and golden
templates are intentionally separate from Terraform state.

## Failure behaviour
- AL2023 has no supported QEMU guest agent package, so the Proxmox builder uses
  a reserved static build address and explicit SSH host instead of agent-based
  IP discovery.
- The shared golden image deliberately excludes runtime container images. This
  is currently a blocker for the isolated LocalStack rehearsal VM: it cannot
  pull its initial images after deployment. The required next step is a
  Proxmox-only fixture image/template derived from the golden template with the
  LocalStack, registry, and TLS-shim images preloaded.

## Verification commands
```bash
infra/tests/images/validate.sh
cd infra/images/packer
packer validate -syntax-only .
```

The local rehearsal has also exercised the source-template build and creation
of template `9000`. The fixture-template stage remains unimplemented.

## Related documents

- [[Cloud deployment]]
- [[Packer implementation]]
- [[Deployment model]]
- [[Proxmox rehearsal implementation]]
- [[Infrastructure resources]]
