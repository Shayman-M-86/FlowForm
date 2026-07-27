---
title: Proxmox rehearsal setup
aliases: ["Proxmox rehearsal setup"]
document_type: workflow
status: verified
authority: canonical
verified_evidence_digest: sha256:3cc1f93cc619710125a2dd68e116f36c9b7a7fc5622b8764d6a576b0f8cd6771
last_edited: 2026-07-27
tags: [infrastructure, tooling]
related_code:
  - "../../../../infra/images/scripts/image"
  - "../../../../infra/deployment/proxmox/host/setup-host.sh"
  - "../../../../infra/deployment/proxmox/terraform/"
  - "../../../../infra/deployment/proxmox/scripts/rehearsal"
related_docs:
  - "Proxmox rehearsal"
  - "Proxmox rehearsal fixtures and egress"
  - "Proxmox rehearsal observability"
---

# Proxmox rehearsal setup

Provides the supported command sequence for creating or replacing the local
Proxmox rehearsal. It requires a workstation with the repository, Docker,
Terraform, Packer, and SSH access to the Proxmox host; it is not a claim that
those prerequisites are installed or configured on any particular machine.

```text
prepare local inputs
        |
setup private host bridge
        |
prepare/build templates
        |
Terraform creates four VMs
        |
sync secrets + converge guests + publish images
        |
verify services, egress, TLS, database, and clocks
```

## Prepare local inputs

Create the gitignored Packer source and Proxmox variable files from their
examples, configure the Terraform variables including SSH public keys, and
provide the machine-local development inputs required by `rehearsal` (including
the non-secret Auth0 identifiers and any secret-source configuration). Do not
put real Auth0 or Grafana secrets in Terraform variables or checked-in files.

## Create the host and templates

On the Proxmox host, run:

```sh
infra/deployment/proxmox/host/setup-host.sh
```

From the workstation, create the source template and build the Proxmox
templates:

```sh
infra/images/scripts/image prepare proxmox --apply
infra/images/scripts/image build proxmox all
```

Then initialise Terraform and run the orchestration command:

```sh
terraform -chdir=infra/deployment/proxmox/terraform init
infra/deployment/proxmox/scripts/rehearsal build
```

`rehearsal build` owns the ordered deployment, secret sync, guest convergence,
image publication, and final non-disruptive verification. Pass `--fresh` only
when a full replacement of Terraform-managed VMs and snippets is intended;
the host secret bundle remains outside that destroy operation.

## Verify, inspect, and replace

Use `rehearsal verify` for the live egress, TLS, service, database, and clock
checks; `--disruptive` additionally stops Squid to check that egress fails
closed. Use `rehearsal logs` for guest container logs. A direct Terraform
operation should go through `rehearsal terraform <arguments...>` so it gets the
same Auth0 input loading and host preflight as `build`.

Terraform destroy removes Terraform-managed VMs and snippets but not templates,
the private host bridge, workstation trust configuration, or the persistent
host secret bundle. Rebuild through `rehearsal build --fresh` rather than
hand-modifying a created VM.

## Related documents

- [[proxmox-index|Proxmox rehearsal]]
- [[rehearsal-fixtures|Proxmox rehearsal fixtures and egress]]
- [[rehearsal-observability|Proxmox rehearsal observability]]
