# FlowForm Proxmox rehearsal Terraform

Packer owns the reusable image. This Terraform root owns its three rehearsal
clones and the cloud-init snippets attached to them:

| VMID | Role | Network |
| --- | --- | --- |
| 210 | proxy | DHCP on `vmbr0`, `10.10.10.10/24` on `vmbr10` |
| 220 | app | `10.10.10.20/24` on `vmbr10`, no gateway |
| 230 | LocalStack | `10.10.10.30/24` on `vmbr10`, no gateway |

It assumes that Packer has built the golden template (default VMID `9000`) and
that the one-time host bootstrap has created `vmbr10` and enabled snippets on
the configured snippet storage. Those host-level operations are deliberately
outside Terraform's VM lifecycle scope.

## First use

From the repository root:

```bash
infra/deployment/proxmox/terraform/render-cloud-init.sh
cd infra/deployment/proxmox/terraform
cp terraform.tfvars.example terraform.tfvars
# Set the Proxmox endpoint, API token, node, storage, and SSH public key.
terraform init
terraform plan
terraform apply
```

The renderer runs locally and Terraform uploads only its generated snippets to
Proxmox. No FlowForm checkout is required on the Proxmox host.

Terraform uses your SSH agent to upload Proxmox snippets. Before running
Terraform, load the same key used for host administration:

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/proxmox_codex
ssh-add -L
```

The provider connects as `root`; the private key is never placed in Terraform
variables or state. The `ssh_public_keys` values are embedded in each custom
cloud-init payload because Proxmox custom user data replaces, rather than
merges with, its generated user-data configuration.

`terraform destroy` removes only the Terraform-managed rehearsal VMs and
snippet files. It does not remove Packer template `9000` or `vmbr10`.

## Current limitation

All three VMs currently clone the shared golden template `9000`. This works
for the proxy because it has LAN egress, but LocalStack `230` is isolated on
`vmbr10` and cannot pull its initial container images from Docker Hub. The
next Packer stage must produce an offline-capable, Proxmox-only LocalStack
fixture template. Once it exists, this Terraform root will use that template
for `localstack` while retaining `9000` for proxy and app.
