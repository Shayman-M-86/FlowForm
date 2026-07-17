# Proxmox platform orchestration

This directory owns Proxmox rehearsal deployment. Packer image construction
lives under `infra/images`; Terraform owns the cloned VMs and cloud-init
snippets here.

Build the shared golden template and then its offline LocalStack fixture:

```bash
infra/images/scripts/prepare-proxmox-source.sh
infra/images/scripts/build-proxmox-image.sh
infra/images/scripts/build-proxmox-localstack-fixture.sh
infra/images/scripts/verify-proxmox-disk-sizes.sh
```

The source and Packer templates default to the official AL2023 image's native
25 GiB disk. Terraform full clones inherit that size and never runs a resize;
existing larger clones must be deliberately replaced to adopt it.

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
golden template `9000` for proxy/app and fixture template `9001` for LocalStack.
Environment-specific values and
fixtures remain under
`infra/containers/rehearsal`; the rendered cloud-init starts shared runtime
bootstrap and Compose files.

The fixture contains only the image layers referenced by the maintained
LocalStack, registry, and TLS-shim Compose files. Runtime configuration and
startup remain owned by cloud-init and Compose.

## Current rehearsal status

The Packer golden template and Terraform topology have been exercised on the
local Proxmox host: Terraform creates and starts proxy `210`, app `220`, and
LocalStack `230`. The proxy cloud-init completes and its Caddy and Squid
containers run. The app and LocalStack VMs also boot with their intended
network isolation and cloud-init.

LocalStack `230` has no default route by design. Its Packer fixture preloads the
third-party images it needs before isolation, while Terraform cloud-init still
creates and starts LocalStack, the local registry, and the TLS shim at runtime.
An applied rehearsal still requires a fixture template built from the current
Compose image references; checked-in configuration alone does not prove the
live services healthy.

## Push the backend image

From a WSL checkout with Docker available, run:

```bash
infra/containers/rehearsal/services/registry/build-and-push-backend.sh
```

The helper builds the production-runtime backend image and pushes it as
`10.10.10.30:5000/flowform-backend:rehearsal`. When the registry is not directly
reachable, it uses `~/.ssh/proxmox_codex` to add `10.10.10.1/24` temporarily to
the Proxmox `vmbr10` bridge, then streams the built image over SSH to app VM
`220`, whose Docker daemon pushes it to the private registry. Its exit trap
removes the address if that invocation added it. The registry is never exposed
on the LAN, and Docker Desktop needs no insecure-registry configuration.

The same invocation mirrors private-registry runtime dependencies declared by
the rehearsal app Compose override. Their upstream names and tags are derived
from that Compose file; currently this publishes `postgres:17` for the two
ephemeral rehearsal databases.

The rehearsal app override recreates its throwaway containers when bootstrap
is rerun so newly generated LocalStack secrets cannot leave PostgreSQL using an
old password. Because deployable migrations are not yet present in the
repository, a rehearsal-only one-shot initializes the current SQLAlchemy schema
before the backend starts; AWS environments remain migration-owned.

The rehearsal runtime contract disables Auth0 Management API validation during
startup because the isolated environment uses placeholder Auth0 credentials.
The backend default remains enabled for other environments, and Management API
operations still fail closed if those credentials are used.

The connection defaults can be overridden with `PROXMOX_SSH_TARGET`,
`PROXMOX_SSH_KEY`, `PROXMOX_PRIVATE_BRIDGE`, `PROXMOX_TEMP_BRIDGE_CIDR`,
and `PUSH_RELAY_SSH_TARGET`.
