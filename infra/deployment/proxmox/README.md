# Proxmox platform orchestration

This directory owns Proxmox rehearsal deployment. Packer image construction
lives under `infra/images`; Terraform owns the cloned VMs and cloud-init
snippets here.

Build the shared golden template through the machine-image pipeline first:

```bash
infra/images/proxmox/provisioning/02-build-proxmox-template.sh
```

Then create the rehearsal topology from the local checkout:

```bash
host/01-setup-host.sh # one-time bootstrap, run on the PVE host
./terraform/render-cloud-init.sh
cd terraform
terraform init
terraform plan
terraform apply
```

Terraform renders no repository files on the Proxmox host. Its local
`render-cloud-init.sh` produces snippets that Terraform uploads before cloning
template `9000` into the rehearsal VMs. Environment-specific values and
fixtures remain under
`infra/containers/rehearsal`; the rendered cloud-init starts shared runtime
bootstrap and Compose files.

The initial Terraform topology clones golden template `9000` for proxy, app,
and LocalStack. A LocalStack-specific Packer fixture template is the next
required image stage; it will replace only the LocalStack clone source.

## Current rehearsal status

The Packer golden template and Terraform topology have been exercised on the
local Proxmox host: Terraform creates and starts proxy `210`, app `220`, and
LocalStack `230`. The proxy cloud-init completes and its Caddy and Squid
containers run. The app and LocalStack VMs also boot with their intended
network isolation and cloud-init.

The rehearsal is not end-to-end healthy yet. LocalStack `230` has no default
route by design, but its current cloud-init attempts to pull LocalStack and
registry images from Docker Hub. Those pulls fail, which prevents LocalStack,
the local registry, and the TLS shim from starting. The next implementation
stage is a Proxmox-only Packer fixture template derived from golden template
`9000` that preloads these required images; Terraform should then clone VM
`230` from that fixture template instead of the shared golden image.
