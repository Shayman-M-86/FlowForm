# Proxmox platform orchestration

This directory owns Proxmox rehearsal deployment. Packer image construction
lives under `infra/images`; Terraform owns the cloned VMs and cloud-init
snippets here.

Build the shared golden template and then its two offline fixtures:

```bash
infra/images/scripts/prepare-proxmox-source.sh
infra/images/scripts/build-proxmox-image.sh
infra/images/scripts/build-proxmox-localstack-fixture.sh
infra/images/scripts/build-proxmox-db-fixture.sh
infra/images/scripts/verify-proxmox-disk-sizes.sh
```

The source and Packer templates default to the official AL2023 image's native
25 GiB disk. Terraform full clones inherit that size and never runs a resize;
existing larger clones must be deliberately replaced to adopt it.

Then create and converge the rehearsal topology from the local checkout:

```bash
host/setup-host.sh # one-time bootstrap, run on the PVE host
terraform -chdir=terraform init
scripts/rehearsal build
```

`rehearsal` is the workstation entrypoint. Its `build` subcommand applies
Terraform, synchronises the PVE-host secret bundle, converges proxy and database,
publishes the two app images, and finally converges the app. Use
`scripts/rehearsal --help` for `verify`, `logs`, `sync`, and `rotate` commands.
Direct Terraform operations use `scripts/rehearsal terraform <arguments...>`.

The full from-scratch order of operations (fresh Proxmox host, nothing built)
is documented in
[docs/40-implementation/proxmox-rehearsal.md](../../../docs/40-implementation/proxmox-rehearsal.md).

Terraform renders no repository files on the Proxmox host. It renders the
checked-in cloud-init templates and uploads the resulting snippets before
cloning golden template `9000` for proxy/app, fixture template `9001` for
LocalStack, and fixture template `9002` for PostgreSQL.
Environment-specific values and
fixtures remain under
`infra/containers/strategies/rehearsal`; the rendered cloud-init starts shared runtime
bootstrap and Compose files.

Template `9001` contains only image layers referenced by the maintained
LocalStack, registry, and TLS-shim Compose files. Template `9002` contains only
the PostgreSQL image declared by DB Compose. Runtime configuration and startup
remain owned by cloud-init and Compose.

## Current rehearsal status

The prior three-VM topology was exercised end-to-end. The checked-in topology
now also creates database VM `240`; that four-VM cutover still requires a fresh
Packer build and live apply before it can be called proven. The proxy remains at
the static LAN address `192.168.70.63` (`proxy_lan_ip` — keep it excluded from
the router's DHCP pool).

Operator TLS trust is anchored on the committed rehearsal CA
(`infra/containers/strategies/rehearsal/services/tls-shim/ca/rehearsal-ca.crt`): the proxy
Caddy serves a pre-generated leaf for `api.localstack.test` signed by it, so
installing that one CA file in a workstation trust store survives all VM
rebuilds. Tail service logs with `infra/deployment/proxmox/scripts/rehearsal logs`.

LocalStack `230` has no default route by design. Its Packer fixture preloads the
third-party images it needs before isolation, while Terraform cloud-init still
creates and starts LocalStack, the local registry, and the TLS shim at runtime.
An applied rehearsal still requires a fixture template built from the current
Compose image references; checked-in configuration alone does not prove the
live services healthy.

## Image publication

`scripts/rehearsal build` publishes both required app images in dependency
order. To publish only the backend image manually from a WSL checkout with
Docker available, run:

```bash
infra/containers/strategies/rehearsal/services/registry/build-and-push-backend.sh
```

The helper builds the production-runtime backend image and pushes it as
`registry.localstack.test/flowform-backend:rehearsal`. It uses
`~/.ssh/proxmox_codex` to add `10.10.10.1/24` temporarily to the Proxmox
`vmbr10` bridge, then streams the built image over SSH to app VM `220`, whose
Docker daemon pushes it. The push rides Squid — `CONNECT
registry.localstack.test:443` → TLS shim → private registry — the same egress
path a real ECR push takes; there is no insecure-registry configuration
anywhere, and the registry is never LAN-facing. Its exit trap removes the
bridge address if that invocation added it.

The helper publishes only the backend image. PostgreSQL is independently
preloaded in Packer fixture `9002`; VM `240` starts it with `pull_policy: never`
after running the maintained initialization tree against both databases.

Auth0 is the one dependency the rehearsal does not fake: bearer tokens and the
Management API use the real dev tenant through the rehearsal Squid allow-list.
The management secret is resolved at deploy time and enters LocalStack only via
`rehearsal sync`; it is not stored in Terraform state or the persistent bundle.

A `terraform destroy` wipes the registry and LocalStack state with VM `230`, but
does not touch `/var/lib/flowform/rehearsal-secrets/<scope>/` on the PVE host.
Use `scripts/rehearsal build --fresh` to destroy and rebuild while preserving
that bundle; the command verifies its fingerprint across the operation.

Connection defaults can be overridden consistently with `PVE_HOST`, `PVE_USER`,
`PVE_SSH_KEY`, `GUEST_USER`, `BRIDGE`, and `BRIDGE_CIDR`.
