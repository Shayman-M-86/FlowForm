# FlowForm Proxmox rehearsal Terraform

Packer owns the reusable image. This Terraform root owns its three rehearsal
clones and the cloud-init snippets attached to them:

| VMID | Role | Network |
| --- | --- | --- |
| 210 | proxy | DHCP on `vmbr0`, `10.10.10.10/24` on `vmbr10` |
| 220 | app | `10.10.10.20/24` on `vmbr10`, no gateway |
| 230 | LocalStack | `10.10.10.30/24` on `vmbr10`, no gateway |

It assumes that Packer has built the golden template (default VMID `9000`) and
the Proxmox-only LocalStack fixture derived from it (default VMID `9001`), and
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
snippet files. It does not remove Packer templates `9000`/`9001` or `vmbr10`.

## Template selection

Proxy `210` and app `220` clone `golden_template_vmid`. LocalStack `230` clones
`localstack_fixture_template_vmid`, whose preloaded image layers allow its
runtime cloud-init and Compose services to start without internet access.
Terraform supplies all networking, keys, Compose/configuration files, service
units, TLS material, and startup actions; none of those are baked by Packer.

Build order is source template, golden template, LocalStack fixture template,
then Terraform. Terraform never invokes either Packer build.

Terraform declares no guest disk resize. New full clones inherit the selected
template's virtual disk size (25 GiB with the current native-size image build).
Older 32 GiB rehearsal clones are not shrunk and must be replaced if they need
to adopt the smaller template.
