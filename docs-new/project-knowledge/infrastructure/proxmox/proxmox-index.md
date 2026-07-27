---
title: Proxmox rehearsal
aliases: ["Proxmox rehearsal"]
document_type: overview
status: verified
authority: canonical
verified_against_commit: 0edae9082dc3381cc1376e8a81276bf5c7bebf88
tags: [infrastructure]
related_code:
  - "../../../../infra/deployment/proxmox/terraform/"
  - "../../../../infra/deployment/proxmox/cloud-init/templates/"
  - "../../../../infra/deployment/proxmox/scripts/"
related_docs:
  - "Infrastructure knowledge"
  - "Proxmox rehearsal fixtures and egress"
  - "Proxmox rehearsal observability"
  - "Proxmox rehearsal setup"
---

# Proxmox rehearsal

Owns the checked-in local rehearsal deployment: Terraform creates four VMs,
cloud-init supplies their guest configuration, and the workstation-side
`rehearsal` command performs convergence. This is a local Proxmox environment,
not evidence of a healthy deployed rehearsal or an AWS deployment.

## Topology and ownership

Terraform clones the proxy and app VMs from golden template `9000`; the
LocalStack and PostgreSQL VMs use fixture templates `9001` and `9002`.

| VMID | Role | Private address | Network boundary |
| --- | --- | --- | --- |
| 210 | Proxy | `10.10.10.10/24` | Also has static LAN address `192.168.70.63/22` on `vmbr0`. |
| 220 | App | `10.10.10.20/24` | Only on `vmbr10`; no gateway is configured. |
| 230 | LocalStack fixtures | `10.10.10.30/24` | Only on `vmbr10`. |
| 240 | PostgreSQL | `10.10.10.40/24` | Only on `vmbr10`; no gateway is configured. |

`setup-host.sh` creates `vmbr10` without physical bridge ports or a gateway and
enables Proxmox snippet storage. Terraform renders and uploads the four custom
cloud-init snippets, attaches them to the clones, and embeds the configured SSH
public keys. The static proxy LAN address is intentional: it is the
operator-facing address and must be excluded from the LAN DHCP pool.

Packer and Terraform are separate boundaries. Image preparation builds the
templates; Terraform consumes their VMIDs and does not invoke Packer.

## Operational entry point

`infra/deployment/proxmox/scripts/rehearsal` is the workstation entry point.
Its supported subcommands are `build`, `verify`, `logs`, `sync`, `rotate`, and
`terraform`. A build optionally destroys the Terraform-managed VMs when passed
`--fresh`, then applies Terraform, synchronises secrets, converges guests,
publishes required images through the isolated relay, and runs verification.
The host-side secret bundle is deliberately outside Terraform's lifecycle.

The focused documents describe the rest of this branch:

- [[rehearsal-fixtures|Proxmox rehearsal fixtures and egress]] — local AWS-like
  fixtures, the registry, and controlled external dependencies.
- [[rehearsal-observability|Proxmox rehearsal observability]] — log access and
  Alloy signal forwarding.
- [[rehearsal-setup|Proxmox rehearsal setup]] — machine-local prerequisites and
  the supported setup and teardown commands.

## Related documents

- [[infrastructure-index|Infrastructure knowledge]]
- [[rehearsal-fixtures|Proxmox rehearsal fixtures and egress]]
- [[rehearsal-observability|Proxmox rehearsal observability]]
- [[rehearsal-setup|Proxmox rehearsal setup]]
