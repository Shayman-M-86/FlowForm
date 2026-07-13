# Proxmox runtime orchestration

This directory is only for Proxmox-specific host setup, snippet rendering,
template cloning, local networking and VM destruction. Packer image construction
lives in `infra/images`; runtime bootstrap lives in `infra/runtime`; rehearsal
fixtures live in `infra/environments/rehearsal`.

## Build the template

From a developer machine or CI runner with Proxmox API access, first import the
official Amazon Linux 2023 KVM qcow2 image into Proxmox as a minimal base
template named by `proxmox_source_template`; Packer then clones that base and
owns FlowForm image provisioning:

```bash
cd infra/images/packer
cp variables/local.auto.pkrvars.hcl.example local.auto.pkrvars.hcl
packer init .
packer validate -syntax-only .
packer build -only='proxmox-clone.amazon_linux_2023' .
```

`create-template.sh` is a compatibility wrapper around the same Packer flow.

## Prepare and run local VMs

On the Proxmox host, from a synced checkout:

```bash
./setup-host.sh
./create-vms.sh --force
```

Defaults:

| VMID | Role | Template |
| --- | --- | --- |
| 210 | proxy | `TEMPLATE_VMID` (default 9000) |
| 220 | app | `TEMPLATE_VMID` (default 9000) |
| 230 | LocalStack/fixtures | `LS_TEMPLATE_VMID`, defaulting to `TEMPLATE_VMID` |
| 240 | optional dev box | `DEV_TEMPLATE_VMID`, defaulting to `TEMPLATE_VMID` |

Runtime cloud-init templates live in `../runtime/cloud-init/` and are rendered
by `./render-user-data.sh` before clone startup.
