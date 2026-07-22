---
title: Proxmox rehearsal setup
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
---

# Proxmox rehearsal setup

The order of operations to stand up the Proxmox rehearsal on a fresh host, and
to tear it down and rebuild. It describes the checked-in scripts; every step is a
maintained entry point, not a hand-applied change. For the topology these steps
produce, see [[Proxmox rehearsal implementation]]; for the fixture/egress model
they exercise, see [[Proxmox rehearsal fixtures and egress]].

## From-scratch setup

The complete order of operations on a fresh Proxmox host with nothing built,
starting from a workstation (WSL) with the repo, Docker, Terraform, Packer, and
SSH access to the Proxmox host. Every step is a checked-in script; none of the
built state is hand-maintained, so this sequence is also the recovery path
after losing the host entirely.

**1. Machine-local configuration (gitignored, one-time).** Copy and fill:

- `infra/images/packer/variables/proxmox.auto.pkrvars.hcl.example` → `.hcl` —
  Proxmox endpoint/credentials for Packer.
- `infra/images/scripts/.env.example` → `.env` — image-build settings.
- `infra/deployment/proxmox/terraform/terraform.tfvars.example` →
  `terraform.tfvars` — Proxmox API endpoint and token, node name, storage
  pools, and the SSH public keys baked into every VM.
- `infra/env/dev/.backend.env` — the dev backend env (shared with the dev
  Compose stack); the Terraform wrapper reads the Auth0 values from it.

**2. Proxmox host bootstrap (once, on the PVE host):**

```bash
infra/deployment/proxmox/host/setup-host.sh
```

Creates the isolated `vmbr10` bridge and enables snippet storage.

**3. Build the templates (Packer, from the workstation):**

```bash
infra/images/scripts/prepare-proxmox-source.sh            # source template 8999
infra/images/scripts/build-proxmox-image.sh               # golden template 9000
infra/images/scripts/build-proxmox-localstack-fixture.sh  # offline fixture 9001
infra/images/scripts/build-proxmox-db-fixture.sh          # offline DB fixture 9002
infra/images/scripts/verify-proxmox-disk-sizes.sh
```

**4. Deploy the topology (Terraform):**

```bash
cd infra/deployment/proxmox/terraform
terraform init
../scripts/with-dev-auth0-env.sh apply
```

The wrapper exports the Auth0 `TF_VAR_*`s; plain `terraform apply` will prompt
for them. The apply clones templates into VMs 210/220/230/240; the LocalStack VM
seeds parameters and secrets on first boot. The app and DB boot independently;
backend readiness recovers after the database becomes healthy. The app VM's
bootstrap does not fail on the empty registry — it **waits** for its images,
retrying the pull, and converges on its own once the next step lands them. No
manual re-bootstrap is needed in the happy path.

**5. Push the two images the app box needs.** The app Compose stack pulls
**both** the backend and the Grafana Alloy sidecar, and the offline app box can
fetch neither from the internet — only from the fake registry. Push both:

```bash
infra/containers/strategies/rehearsal/services/registry/build-and-push-backend.sh
infra/containers/strategies/rehearsal/services/registry/mirror-alloy-image.sh
```

Both relay through app VM 220's Docker daemon, so they require step 4's VMs to be
running — the ordering apply → push is inherent. `compose pull` fails as a whole
if *any* service image is missing, so mirroring Alloy is not optional: skip it
and the bootstrap's waiting pull retries forever on the absent alloy image, which
looks exactly like a stuck backend pull. Once both images land, the waiting pull
succeeds and the backend comes up; you do not re-run the app one-shot yourself.

**Steps 4–5 in one command.** `rebuild.sh` orchestrates apply → push backend →
mirror Alloy in the one order they can go in (see the "why this order is
inherent" note in its header). It calls the same wrapper and both registry
scripts under the hood:

```bash
infra/deployment/proxmox/scripts/rebuild.sh                 # converge + push both images
infra/deployment/proxmox/scripts/rebuild.sh --fresh -- -auto-approve  # full teardown first
```

`--fresh` runs `terraform destroy` before the apply (opt-in, so a bare run never
nukes a healthy stack); anything after `--` is passed through to the terraform
apply.

**6. Operator workstation trust (once per machine).** Add the hosts entry
`192.168.70.63 api.localstack.test` (Windows: `C:\Windows\System32\drivers\etc\hosts`;
also WSL's `/etc/hosts` if testing from there), then install
`infra/containers/strategies/rehearsal/services/tls-shim/ca/rehearsal-ca.crt` into the
trust store — Windows: import into *Trusted Root Certification Authorities*;
Firefox keeps its own store; Node tooling needs
`NODE_EXTRA_CA_CERTS=<path to rehearsal-ca.crt>`. Because the CA is a repo
file, this never has to be repeated after rebuilds.

**7. Verify:**

```bash
curl --cacert infra/containers/strategies/rehearsal/services/tls-shim/ca/rehearsal-ca.crt \
  https://api.localstack.test/api/v1/system/health/ready   # 200, verified TLS
infra/deployment/proxmox/scripts/logs.sh app --list        # containers healthy
infra/deployment/proxmox/scripts/verify.sh                 # full egress model
```

`verify.sh` is the definitive check: health `200`, a structurally
valid but unsigned JWT returning `401` (kid mismatch — the live Auth0 JWKS path,
never a `500`), every fake-AWS/ECR name appearing as a `CONNECT` in Squid's
access log, and the direct-bypass paths all blocked. `--disruptive` also stops
Squid to prove egress fails closed. Note it reads Squid's log as the in-container
squid uid (`docker exec -u 13`), which the hardened container requires.

**Teardown and rebuild.** `terraform destroy` removes the VMs and with them the
registry contents and all seeded state. After any full rebuild, repeat steps
4–5 — or run `rebuild.sh --fresh`, which folds the destroy, apply, and push into
one command (the templates, host bridge, and workstation trust all survive). VM
disks are disposable by design; fixes belong in the scripts and templates, never
hand-applied to a built VM.

## Related documents

- [[Proxmox rehearsal implementation]]
- [[Proxmox rehearsal fixtures and egress]]
- [[Proxmox rehearsal observability]]
