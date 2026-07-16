---
title: Proxmox rehearsal implementation
document_type: implementation
status: draft
authority: canonical
verified_against_commit: null
tags: [infrastructure]
related_code:
  - "../../infra/images/proxmox/provisioning/"
  - "../../infra/images/packer/"
  - "../../infra/deployment/proxmox/host/"
  - "../../infra/deployment/proxmox/terraform/"
related_docs:
  - "Deployment model"
  - "Machine image building"
  - "Packer implementation"
  - "Infrastructure implementation"
---

# Proxmox rehearsal implementation

Maps the local Proxmox rehearsal boundary to its maintained entry points. It
describes the checked-in design and the observed LocalStack limitation; it does
not claim that the rehearsal is end-to-end healthy.

## Ownership boundary

| Layer | Owned responsibility | Main location |
| --- | --- | --- |
| Source preparation | Import the pinned official AL2023 KVM image as a minimal Proxmox source template. | `infra/images/proxmox/provisioning/01-prepare-proxmox-source.sh` |
| Packer | Build the shared reusable golden template from that source. | `infra/images/packer/`, `infra/images/proxmox/provisioning/02-build-proxmox-template.sh` |
| Host bootstrap | Create the private rehearsal bridge and enable Proxmox snippet storage once. | `infra/deployment/proxmox/host/01-setup-host.sh` |
| Terraform | Render/upload cloud-init and clone the golden template into the rehearsal topology. | `infra/deployment/proxmox/terraform/` |

Packer and Terraform are separate processes. Packer produces a reusable
template; Terraform consumes a completed template by VMID. Terraform does not
invoke Packer, so a base-image change requires a Packer build before Terraform
can deploy clones of that new template.

## Current topology

The shared golden template is VMID `9000`. Terraform currently declares:

| VMID | Role | Source | Network |
| --- | --- | --- | --- |
| 210 | Proxy | Golden `9000` | DHCP on `vmbr0`; `10.10.10.10/24` on `vmbr10` |
| 220 | App | Golden `9000` | `10.10.10.20/24` on `vmbr10`; no gateway |
| 230 | LocalStack | Golden `9000` | `10.10.10.30/24` on `vmbr10`; no gateway |

Terraform renders cloud-init locally, embeds its configured public SSH keys in
the custom user-data, uploads the snippets to Proxmox storage, and attaches
them to the clone. This matters because Proxmox custom user data replaces its
generated user-data rather than merging the generated SSH-key section.

## Verified limitation and next stage

The proxy can start its Docker-based Caddy and Squid services because it has
LAN egress. LocalStack intentionally has no default route, so its current
first-boot `docker compose` commands cannot pull third-party images from Docker
Hub. LocalStack, the local registry, and TLS shim therefore do not start; the
app has no local registry backend to consume.

The next image implementation is a Proxmox-only LocalStack fixture template:
clone the shared golden template in Packer, preload the required LocalStack,
registry, and TLS-shim images, and configure Terraform to use that fixture only
for VM `230`. The shared golden template must remain application-image-free.

## Related documents

- [[Deployment model]]
- [[Machine image building]]
- [[Packer implementation]]
- [[Infrastructure implementation]]
