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
./with-dev-auth0-env.sh plan
./with-dev-auth0-env.sh apply
```

Run plan/apply through `with-dev-auth0-env.sh`: the Auth0 identifiers are
Terraform variables without defaults, and the wrapper exports them as
`TF_VAR_*` from the gitignored `infra/env/dev/.backend.env` so the rehearsal
always validates tokens against the same dev tenant the front end logs in to.

The full from-scratch order of operations (fresh Proxmox host, nothing built)
is documented in
[docs/40-implementation/proxmox-rehearsal.md](../../../docs/40-implementation/proxmox-rehearsal.md).

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

The topology has been exercised end-to-end on the local Proxmox host: Terraform
creates and starts proxy `210`, app `220`, and LocalStack `230`; the app boots,
seeds from LocalStack, and serves `/api/v1/system/health/ready` through the
proxy at the static LAN address `192.168.70.63` (`proxy_lan_ip` — keep it
excluded from the router's DHCP pool). Bearer-token validation against the real
dev Auth0 tenant has been verified through Squid: a well-formed but unsigned
JWT returns `401` (JWKS kid mismatch), not a proxy error.

Operator TLS trust is anchored on the committed rehearsal CA
(`infra/containers/rehearsal/services/tls-shim/ca/rehearsal-ca.crt`): the proxy
Caddy serves a pre-generated leaf for `api.localstack.test` signed by it, so
installing that one CA file in a workstation trust store survives all VM
rebuilds. Tail service logs with `infra/deployment/proxmox/rehearsal-logs.sh`.

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

Auth0 is the one dependency the rehearsal does not fake: bearer tokens are
validated against the real dev tenant (its issuer domain is on the rehearsal
Squid allow-list), so Studio-issued tokens verify end-to-end. Only the
Management API stays on placeholder credentials — its client secret is seeded
as random bytes — so the runtime contract disables Management API validation
during startup. The backend default remains enabled for other environments,
and Management API operations still fail closed.

A `terraform destroy` wipes the registry contents with VM `230`; after any
full rebuild, re-run the push above and then re-run
`/opt/flowform/scripts/run-bootstrap-app.sh` on app VM `220` (its first boot
fails at image pull by design when the registry is empty).

The connection defaults can be overridden with `PROXMOX_SSH_TARGET`,
`PROXMOX_SSH_KEY`, `PROXMOX_PRIVATE_BRIDGE`, `PROXMOX_TEMP_BRIDGE_CIDR`,
and `PUSH_RELAY_SSH_TARGET`.
