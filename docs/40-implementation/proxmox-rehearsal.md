---
title: Proxmox rehearsal implementation
document_type: implementation
status: draft
authority: canonical
verified_against_commit: null
tags: [infrastructure]
related_code:
  - "../../infra/deployment/proxmox/terraform/"
  - "../../infra/deployment/proxmox/cloud-init/templates/"
  - "../../infra/deployment/config/runtime-parameter-contract.json"
related_docs:
  - "Proxmox rehearsal fixtures and egress"
  - "Proxmox rehearsal observability"
  - "Proxmox rehearsal setup"
  - "Deployment model"
  - "Machine image building"
  - "Packer implementation"
  - "Infrastructure implementation"
---

# Proxmox rehearsal implementation

Maps the local Proxmox rehearsal boundary to its maintained entry points. It
describes the checked-in design; it does not claim that a fixture has been built
or the rehearsal is end-to-end healthy.

This page owns the ownership boundary and the VM topology. The fixture/egress
model, observability, and the from-scratch runbook live in the sibling pages
listed under [Rehearsal areas](#rehearsal-areas) below.

## Ownership boundary

| Layer | Owned responsibility | Main location |
| --- | --- | --- |
| Source preparation | Import the pinned official AL2023 KVM image as a minimal Proxmox source template. | `infra/images/scripts/prepare-proxmox-source.sh` |
| Packer | Build the shared golden template, then derive separate offline LocalStack and PostgreSQL fixtures. | `infra/images/packer/`, `infra/images/scripts/build-proxmox-image.sh`, `infra/images/scripts/build-proxmox-localstack-fixture.sh`, `infra/images/scripts/build-proxmox-db-fixture.sh` |
| Host bootstrap | Create the private rehearsal bridge and enable Proxmox snippet storage once. | `infra/deployment/proxmox/host/setup-host.sh` |
| Terraform | Render cloud-init templates, upload the snippets, and clone the golden template into the rehearsal topology. | `infra/deployment/proxmox/terraform/`, `infra/deployment/proxmox/cloud-init/templates/` |
| Runtime configuration contract | Keep AWS CDK and Proxmox rehearsal SSM parameter names aligned while allowing platform-specific values. | `infra/deployment/config/runtime-parameter-contract.json` |

Packer and Terraform are separate processes. Packer produces a reusable
template; Terraform consumes a completed template by VMID. Terraform does not
invoke Packer, so a base-image change requires a Packer build before Terraform
can deploy clones of that new template.

## Current topology

The default golden template is VMID `9000`; fixture templates are LocalStack
`9001` and PostgreSQL `9002`. The source (`8999`), golden, and fixture templates use the official image's
native 25 GiB virtual disk. Terraform does not resize disks: new full clones
inherit 25 GiB, while older 32 GiB clones remain 32 GiB until replaced.
Terraform declares:

| VMID | Role | Source | Network |
| --- | --- | --- | --- |
| 210 | Proxy | Golden `9000` | Static `192.168.70.63/22` on `vmbr0` (`proxy_lan_ip`); `10.10.10.10/24` on `vmbr10` |
| 220 | App | Golden `9000` | `10.10.10.20/24` on `vmbr10`; no gateway |
| 230 | LocalStack | Fixture `9001` | `10.10.10.30/24` on `vmbr10`; no gateway |
| 240 | Database | Fixture `9002` | `10.10.10.40/24` on `vmbr10`; no gateway |

The proxy's LAN address is static on purpose. It is the one address operators,
docs, and hosts files name, and a DHCP lease does not survive VM recreation:
each rebuild changes the NIC MAC and the machine-id-derived DHCP client
identifier, so the stack came back healthy on a new address while everything
pointing at the old one appeared dead. MAC pinning alone does not fix this.
Keep `proxy_lan_ip` excluded from the LAN router's DHCP pool.

Terraform renders the checked-in cloud-init templates directly, embeds its configured public SSH keys in
the custom user-data, uploads the snippets to Proxmox storage, and attaches
them to the clone. This matters because Proxmox custom user data replaces its
generated user-data rather than merging the generated SSH-key section.

## Rehearsal areas

The rest of the rehearsal is documented in three focused pages:

- [[Proxmox rehearsal fixtures and egress]] — the offline fixture boundary, the
  Squid/TLS-shim egress model, registry pushes, the database VM, and the two
  deliberate holes in the isolation (Auth0 and operator-facing TLS).
- [[Proxmox rehearsal observability]] — tailing container logs with `logs.sh`
  and the two-agent Grafana Alloy log-shipping stack.
- [[Proxmox rehearsal setup]] — the from-scratch runbook (steps 1–7,
  `rebuild.sh`, and teardown).

## Related documents

- [[Proxmox rehearsal fixtures and egress]]
- [[Proxmox rehearsal observability]]
- [[Proxmox rehearsal setup]]
- [[Deployment model]]
- [[Machine image building]]
- [[Packer implementation]]
- [[Infrastructure implementation]]
