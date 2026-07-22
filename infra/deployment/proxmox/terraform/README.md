# FlowForm Proxmox rehearsal Terraform

Packer owns the reusable images. This Terraform root owns its four rehearsal
clones and the cloud-init snippets attached to them:

| VMID | Role | Network |
| --- | --- | --- |
| 210 | proxy | DHCP on `vmbr0`, `10.10.10.10/24` on `vmbr10` |
| 220 | app | `10.10.10.20/24` on `vmbr10`, no gateway |
| 230 | LocalStack | `10.10.10.30/24` on `vmbr10`, no gateway |
| 240 | PostgreSQL | `10.10.10.40/24` on `vmbr10`, no gateway |

It assumes that Packer has built the golden template (default VMID `9000`) and
the Proxmox-only LocalStack and PostgreSQL fixtures derived from it (default
VMIDs `9001` and `9002`), and
that the one-time host bootstrap has created `vmbr10` and enabled snippets on
the configured snippet storage. Those host-level operations are deliberately
outside Terraform's VM lifecycle scope.

## First use

From the repository root:

```bash
cd infra/deployment/proxmox/terraform
cp terraform.tfvars.example terraform.tfvars
# Set the Proxmox endpoint, API token, node, storage, and SSH public key.
terraform init
../scripts/rehearsal terraform plan
../scripts/rehearsal terraform apply
# Or run the complete apply/sync/converge workflow:
../scripts/rehearsal build
```

Terraform renders `../cloud-init/templates/*.yaml.tftpl` directly from the
checked-in bootstrap, Compose, and TLS sources, then uploads the snippets to
Proxmox. No rendered cloud-init file or FlowForm checkout is required on the
Proxmox host.

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
snippet files. It does not remove Packer templates `9000`/`9001`/`9002`,
`vmbr10`, or the root-only rehearsal secret bundle stored on the PVE host.

## Template selection

Proxy `210` and app `220` clone `golden_template_vmid`. LocalStack `230` clones
`localstack_fixture_template_vmid`, whose preloaded image layers allow its
runtime cloud-init and Compose services to start without internet access.
Database `240` clones `db_fixture_template_vmid`, which preloads only the
PostgreSQL image declared by the rehearsal DB Compose file.
Terraform supplies all networking, keys, Compose/configuration files, service
units, TLS material, and startup actions; none of those are baked by Packer.

## LocalStack runtime seeding

LocalStack remains reachable only on the isolated `vmbr10` network. Terraform
does not use the AWS provider against LocalStack and does not expose port 4566
to the development LAN. Instead, Terraform validates `localstack_seed_values`
against `infra/deployment/config/runtime-parameter-contract.json`, renders the
non-secret values into cloud-init, and uploads them with the LocalStack VM
snippet.

On every fixture VM boot, `flowform-localstack-seed.service` waits for
LocalStack health and runs the idempotent non-secret seed locally. Managed
Secrets Manager values and the linkage-secret ARN parameter are reconciled by
`../scripts/rehearsal sync`, which streams an allow-listed archive assembled
from the PVE-host bundle and deploy-time inputs. Secret values never enter
Terraform configuration or state. App, proxy, and database bootstrap AWS reads
retry while these boot-time/deploy-time steps complete.

The default non-secret values live in `variables.tf`. To override them, set the
complete `localstack_seed_values` map in `terraform.tfvars`; Terraform rejects
missing or unknown keys so contract changes cannot silently leave stale seed
data. Because LocalStack persistence is disabled, the fixture VM is the
lifecycle boundary: each boot starts empty and reseeds deterministically.

Build order is source template, golden template, LocalStack fixture template,
database fixture template, then Terraform. Terraform never invokes Packer.

Terraform declares no guest disk resize. New full clones inherit the selected
template's virtual disk size (25 GiB with the current native-size image build).
Older 32 GiB rehearsal clones are not shrunk and must be replaced if they need
to adopt the smaller template.
