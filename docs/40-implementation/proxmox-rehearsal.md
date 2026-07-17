---
title: Proxmox rehearsal implementation
document_type: implementation
status: draft
authority: canonical
verified_against_commit: null
tags: [infrastructure]
related_code:
  - "../../infra/images/scripts/"
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
describes the checked-in design; it does not claim that a fixture has been built
or the rehearsal is end-to-end healthy.

## Ownership boundary

| Layer | Owned responsibility | Main location |
| --- | --- | --- |
| Source preparation | Import the pinned official AL2023 KVM image as a minimal Proxmox source template. | `infra/images/scripts/prepare-proxmox-source.sh` |
| Packer | Build the shared golden template, then derive the offline LocalStack fixture. | `infra/images/packer/`, `infra/images/scripts/build-proxmox-image.sh`, `infra/images/scripts/build-proxmox-localstack-fixture.sh` |
| Host bootstrap | Create the private rehearsal bridge and enable Proxmox snippet storage once. | `infra/deployment/proxmox/host/01-setup-host.sh` |
| Terraform | Render/upload cloud-init and clone the golden template into the rehearsal topology. | `infra/deployment/proxmox/terraform/` |
| Runtime configuration contract | Keep AWS CDK and Proxmox rehearsal SSM parameter names aligned while allowing platform-specific values. | `infra/deployment/config/runtime-parameter-contract.json` |

Packer and Terraform are separate processes. Packer produces a reusable
template; Terraform consumes a completed template by VMID. Terraform does not
invoke Packer, so a base-image change requires a Packer build before Terraform
can deploy clones of that new template.

## Current topology

The default golden template is VMID `9000` and the default fixture is `9001`.
The source (`8999`), golden, and fixture templates use the official image's
native 25 GiB virtual disk. Terraform does not resize disks: new full clones
inherit 25 GiB, while older 32 GiB clones remain 32 GiB until replaced.
Terraform declares:

| VMID | Role | Source | Network |
| --- | --- | --- | --- |
| 210 | Proxy | Golden `9000` | DHCP on `vmbr0`; `10.10.10.10/24` on `vmbr10` |
| 220 | App | Golden `9000` | `10.10.10.20/24` on `vmbr10`; no gateway |
| 230 | LocalStack | Fixture `9001` | `10.10.10.30/24` on `vmbr10`; no gateway |

Terraform renders cloud-init locally, embeds its configured public SSH keys in
the custom user-data, uploads the snippets to Proxmox storage, and attaches
them to the clone. This matters because Proxmox custom user data replaces its
generated user-data rather than merging the generated SSH-key section.

## Offline fixture boundary

The proxy retains LAN egress and uses the golden template. LocalStack has no
default route, so its fixture preloads the images named by the maintained
LocalStack, registry, and TLS-shim Compose files before deployment. Terraform
uses that fixture only for VM `230`; proxy and app remain on the shared golden
template.

Cloud-init still writes the Compose files, rehearsal TLS material, service
units, SSH keys, and network-specific configuration, then starts the services.
LocalStack remains private to `vmbr10`; Terraform does not require a LAN-facing
LocalStack endpoint or run an AWS provider against it.

Terraform validates its non-secret seed map against the shared parameter
contract and renders both into the LocalStack cloud-init payload. A systemd
oneshot waits for LocalStack health on every boot, generates throwaway secrets
inside the VM, creates local KMS and Secrets Manager resources, and publishes
the resulting local identifiers plus the rehearsal backend/proxy parameters.
The AWS CDK security stack uses the same contract for its scoped SSM names but
supplies real AWS resource values. App and proxy bootstrap reads retry to avoid
a simultaneous-start race with the seed service.

Seed resources remain runtime data; the fixture contains none of that state.
Static validation proves the build graph and contract resolve, not that
template `9001` exists on a Proxmox host or the deployed services are healthy.

The backend image push remains an operator action. The maintained helper at
`infra/containers/rehearsal/services/registry/build-and-push-backend.sh` uses a
direct private-network path when one exists. From WSL or another LAN
workstation, it temporarily addresses the Proxmox host on `vmbr10` and creates a
proxied SSH path to app VM `220`, streams the built image into that VM's Docker
daemon, and pushes from there before removing the temporary transport on exit.
This does not make the registry or LocalStack LAN-facing and does not require an
insecure-registry exception in Docker Desktop.

## Related documents

- [[Deployment model]]
- [[Machine image building]]
- [[Packer implementation]]
- [[Infrastructure implementation]]
