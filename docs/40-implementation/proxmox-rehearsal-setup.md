---
title: Proxmox rehearsal setup
aliases:
  - "Proxmox rehearsal setup"
document_type: implementation
status: draft
authority: canonical
verified_against_commit: null
tags: [infrastructure]
related_code:
  - "../../infra/images/scripts/"
  - "../../infra/images/packer/"
  - "../../infra/deployment/proxmox/host/"
  - "../../infra/deployment/proxmox/terraform/"
  - "../../infra/deployment/proxmox/scripts/"
related_docs:
  - "Proxmox rehearsal implementation"
  - "Proxmox rehearsal fixtures and egress"
  - "Proxmox rehearsal observability"
  - "Deployment model"
---

# Proxmox rehearsal setup

The order of operations to stand up the Proxmox rehearsal on a fresh host, and
to tear it down and rebuild. It describes the checked-in scripts; every step is a
maintained entry point, not a hand-applied change. For the topology these steps
produce, see [[proxmox-rehearsal|Proxmox rehearsal implementation]]; for the fixture/egress model
they exercise, see [[proxmox-rehearsal-fixtures|Proxmox rehearsal fixtures and egress]].

## From-scratch setup

The complete order of operations on a fresh Proxmox host with nothing built,
starting from a workstation (WSL) with the repo, Docker, Terraform, Packer, and
SSH access to the Proxmox host. Every step is a checked-in script; none of the
built state is hand-maintained, so this sequence is also the recovery path
after losing the host entirely.

**1. Machine-local configuration (gitignored, one-time).** Copy and fill:

- `infra/images/packer/variables/proxmox.auto.pkrvars.hcl.example` → `.hcl` —
  Proxmox endpoint/credentials for Packer.
- `infra/images/config/proxmox-source.env.example` → `proxmox-source.env` — image-build settings.
- `infra/deployment/proxmox/terraform/terraform.tfvars.example` →
  `terraform.tfvars` — Proxmox API endpoint and token, node name, storage
  pools, and the SSH public keys baked into every VM.
- `infra/env/dev/.backend.env` — the dev backend env (shared with the dev
  Compose stack); `rehearsal` reads the non-secret Auth0 identifiers from it.
- `infra/env/dev/.grafana.env` — machine-local `GRAFANA_CLOUD_TOKEN` input
  resolved by `rehearsal sync` for proxy observability.

**2. Proxmox host bootstrap (once, on the PVE host):**

```bash
infra/deployment/proxmox/host/setup-host.sh
```

Creates the isolated `vmbr10` bridge and enables snippet storage.

**3. Build the templates (Packer, from the workstation):**

```bash
infra/images/scripts/image prepare proxmox --apply  # create source template 8999
infra/images/scripts/image build proxmox all        # build 9000, 9001, 9002 and verify
```

**4. Deploy and converge the topology:**

```bash
terraform -chdir=infra/deployment/proxmox/terraform init
infra/deployment/proxmox/scripts/rehearsal build
```

`rehearsal build` is the maintained workstation orchestrator and the sole owner
of first convergence. Cloud-init installs configuration and enables app, proxy,
and database systemd services for later VM reboots, but does not start those
services during the creation boot. This avoids cloud-init racing the workstation
over the same bootstrap locks or waiting for images that are not published yet.
This is a rehearsal-only image-relay constraint, not the intended AWS
first-boot contract; [[deployment-model|Deployment model]] owns that distinction.

The orchestrator runs Terraform apply → secret synchronisation → proxy
convergence → app image-relay preparation. It then converges the database while
building the backend and pulling Alloy in parallel, publishes the images through
one prepared relay, converges the app, and runs the non-disruptive verification
suite. A registry upload is skipped only when its manifest config digest exactly
matches the prepared local image; unknown manifest shapes are published normally.
The ordering remains inherent: secret sync requires VM 230; isolated guests and
image publication need Squid; and the app requires both registry images plus its
database. Direct Terraform operations use `rehearsal terraform <arguments...>`
and share the same preparation code.

Use `--fresh` for an explicit full replacement:

```bash
infra/deployment/proxmox/scripts/rehearsal build --fresh -- -auto-approve
```

`--fresh` runs `terraform destroy` before the apply (opt-in, so a bare run never
nukes a healthy stack); anything after `--` is passed through to Terraform.
The root-only bundle at `/var/lib/flowform/rehearsal-secrets/<scope>/` is outside
Terraform's lifecycle. When it already exists, `build --fresh` fingerprints it
before destroy and confirms that it is unchanged after apply and sync.

**5. Synchronise or rotate secrets independently (as needed):**

```bash
infra/deployment/proxmox/scripts/rehearsal sync
infra/deployment/proxmox/scripts/rehearsal rotate app
infra/deployment/proxmox/scripts/rehearsal rotate database
infra/deployment/proxmox/scripts/rehearsal rotate linkage
```

App and database rotations restore the prior bundle values and attempt to
reconverge the prior state if sync or consumer convergence fails. Linkage
history is append-only: after a version is synced, it is retained even if app
convergence fails, and `rehearsal build` is the recovery path.

**6. Operator workstation trust (once per machine).** Add the hosts entry
`192.168.70.63 api.localstack.test` (Windows: `C:\Windows\System32\drivers\etc\hosts`;
also WSL's `/etc/hosts` if testing from there), then install
`infra/containers/strategies/rehearsal/services/tls-shim/ca/rehearsal-ca.crt` into the
trust store — Windows: import into *Trusted Root Certification Authorities*;
Firefox keeps its own store; Node tooling needs
`NODE_EXTRA_CA_CERTS=<path to rehearsal-ca.crt>`. Because the CA is a repo
file, this never has to be repeated after rebuilds.

**7. Verify or inspect independently:**

```bash
curl --cacert infra/containers/strategies/rehearsal/services/tls-shim/ca/rehearsal-ca.crt \
  https://api.localstack.test/api/v1/system/health/ready   # 200, verified TLS
infra/deployment/proxmox/scripts/rehearsal logs app --list # containers healthy
infra/deployment/proxmox/scripts/rehearsal verify          # full egress model
```

`rehearsal build` runs this verification automatically before reporting
success. `rehearsal verify` remains the independent definitive check: health `200`, a structurally
valid but unsigned JWT returning `401` (kid mismatch — the live Auth0 JWKS path,
never a `500`), every fake-AWS/ECR name appearing as a `CONNECT` in Squid's
access log, and the direct-bypass paths all blocked. `--disruptive` also stops
Squid to prove egress fails closed. Note it reads Squid's log as the in-container
squid uid (`docker exec -u 13`), which the hardened container requires.

**Teardown and rebuild.** `terraform destroy` removes the VMs and with them the
registry contents and seeded LocalStack state, but not the PVE-host secret
bundle. Run `rehearsal build --fresh` to fold destroy, apply, sync, publication,
and convergence into one command. Templates, the host bridge, the persistent
bundle, and workstation trust survive. VM disks are disposable by design;
fixes belong in scripts and templates, never hand-applied to a built VM.

## Related documents

- [[proxmox-rehearsal|Proxmox rehearsal implementation]]
- [[proxmox-rehearsal-fixtures|Proxmox rehearsal fixtures and egress]]
- [[proxmox-rehearsal-observability|Proxmox rehearsal observability]]
- [[deployment-model|Deployment model]]
