# Plan: Script Reorg + Proxmox Local Bootstrap Rehearsal Harness

> Standalone execution plan. Safe to pick up cold — no prior-conversation
> context required. Two phases: **Phase 0** cleans up where scripts live so
> VM/bootstrap artifacts have a sensible home; **Phases 1–5** build a
> Proxmox-hosted rehearsal that boots a clean Linux VM into the locked-down
> split-EC2 runtime.

---

## Context / Why

The split-EC2 runtime (public **proxy box**: Caddy + Squid; private **app box**:
backend only) is fully described in CDK, and both production Compose files
exist and are hardened:
- `infra/docker/docker-compose.proxy.yml` (Caddy + Squid)
- `infra/docker/docker-compose.app.yml` (backend only)

But the CDK `ApplicationStack` boots instances into **nothing** — there is a
`TODO: host bootstrap is intentionally deferred` at
`infra/cdk/flowform_infra/stacks/application_stack.py:177`. Everything the
runtime depends on at first boot is unproven: the bootstrap/user-data script,
the Docker daemon proxy drop-in, env-file generation, tmpfs secret
materialization, and forced-proxy egress. The project's own due-diligence
checklist
(`infra/cdk/docs/implementation-sketch/ec2-compose-due-diligence-checklist.md`)
concentrates the remaining risk in exactly these host-bootstrap items.

**Goal:** rehearse the from-clean-boot bootstrap on **real VMs on Proxmox**,
driven by **cloud-init** (the exact artifact EC2 consumes). The bootstrap
scripts authored here are the real production deliverable; the Proxmox harness
just exercises them from a clean machine before we spend time on real EC2.

**Held boundary — do not blur it:**
```
Local Proxmox VMs = prove BOOTSTRAP MECHANICS (real systemd, real Docker
                    daemon config, real two-NIC routing, real tmpfs, real
                    forced-proxy egress).
Staging EC2       = prove the AWS TRUST BOUNDARY (IMDS + hop-limit 2, real
                    route tables, SG enforcement, S3 gateway endpoint for ECR
                    layers, Route 53 DNS-01, RDS SG isolation).
```

## Confirmed decisions

- **Host platform: Proxmox VE.** Real Linux bridges give genuine network
  isolation; LocalStack is just another VM on the private net (no WSL2
  host-bridging hacks).
- **First boot: cloud-init** on an Ubuntu/Debian cloud image. The bootstrap is
  authored as real user-data, directly reusable later as CDK
  `ec2.UserData.for_linux()`.
- **VM creation: `qm` shell scripts** (clone from a cloud-init template).
  Structure user-data so an OpenTofu/Terraform wrapper can adopt it later
  without rework.
- **Golden template, not boot-time installs.** Bake Docker, Docker Compose,
  AWS CLI, curl, jq, nftables into the cloud-init **template**. In the real
  design the app box has no package-mirror route, so an app VM that
  apt-installs Docker at boot would test a path prod does not have. cloud-init
  runs only FlowForm bootstrap logic.
- **Fake AWS: LocalStack** (Secrets Manager, SSM, KMS) on its own VM. Bootstrap
  runs *real* `aws` CLI calls against it via an endpoint override, so the AWS
  code path is exercised, not stubbed.
- **Fake registry: `registry:2`** on the proxy VM for `BACKEND_IMAGE`.
- **Author-for-you-to-run.** I cannot reach the Proxmox host from here. All
  scripts are written into the repo; you run the Proxmox-side pieces and paste
  back output for iteration. (Wiring up direct Proxmox access is a possible
  later convenience, out of scope for this plan.)

## Fidelity constraint to keep honest

Squid allows `CONNECT` only to **443** and allow-lists by **TLS SNI**
(`infra/docker/squid/squid.conf`). LocalStack serves plain HTTP on `:4566`. To
keep "app-box AWS calls ride Squid" TRUE (routing-enforced: the app VM has no
route to LocalStack except via the proxy), front LocalStack with a **TLS
terminator presenting SNI names** in a rehearsal allow-list
(`secretsmanager.localstack.test`, `ssm.localstack.test`,
`kms.localstack.test`), `/etc/hosts` on the app VM resolving them to the
LocalStack VM IP, and Squid's rehearsal allow-list admitting them. The app box
then does exactly what prod does: `CONNECT <host>:443` → Squid → allow → TLS
tunnel. The only deltas from prod are the hostnames and a rehearsal-only CA —
documented in the README so it is never mistaken for AWS proof.

---

## Phase 0 — Script reorganization (do first)

**Problem:** scripts are scattered and mixed by concern. Current state:

```
scripts/
  backend/run_backend_security.sh
  count_lines.sh
  dev/install-git-hooks.sh
  infra/fetch-dev-secrets.sh          # dev secret assembly
  infra/generate-env-files.sh         # env-file generation
  infra/generate-secrets.sh           # throwaway secret gen (wrapper)
  infra/generate_secrets.py           # throwaway secret gen (impl)
  infra/load-core-mock-data.sh        # mock data — different concern
  infra/load-response-mock-data.sh    # mock data — different concern
  lint-md.sh
  shared_script/check-openapi-contracts.sh
  shared_script/sync-openapi.sh
  "start.stop  /bootstrap-dev-and-load-mocks.sh"   # NOTE: dir name has spaces
```

Issues: a directory literally named `start.stop  ` (with trailing spaces);
`infra/` conflates *secret/env plumbing* with *mock-data loaders*; loose
top-level scripts (`count_lines.sh`, `lint-md.sh`); and **no home for
VM/bootstrap artifacts** — which is the whole reason this phase exists.

**Target structure:**

```
scripts/
  dev/                      # local developer workflow
    install-git-hooks.sh
    bootstrap-dev-and-load-mocks.sh    # moved out of "start.stop  /"
    load-core-mock-data.sh             # moved from infra/
    load-response-mock-data.sh         # moved from infra/
  secrets/                  # secret + env plumbing (dev AND prod-bound)
    fetch-dev-secrets.sh
    generate-secrets.sh
    generate_secrets.py
    generate-env-files.sh
  bootstrap/                # NEW — host bootstrap for the EC2/VM runtime
    bootstrap-app.sh                   # (built in Phase 1)
    bootstrap-proxy.sh                 # (built in Phase 1)
  backend/
    run_backend_security.sh
  ci/                       # was shared_script/
    check-openapi-contracts.sh
    sync-openapi.sh
  tools/                    # loose utilities
    count_lines.sh
    lint-md.sh

infra/rehearsal/            # NEW — Proxmox rehearsal harness (Phases 2–4)
```

**Rationale for the split:** `bootstrap/` (runs on a server at boot) must be
visibly separate from `dev/` (runs on a developer laptop) and `secrets/`
(plumbing shared by both) — the user's explicit ask. Mock-data loaders are a
dev concern, not infra secret plumbing, so they move to `dev/`.

**Reference-update sweep** (every path that names a moved script — found via
grep, update all):
- `.github/workflows/ci.yml` lines 58, 115, 207, 217, 322
  (`run_backend_security.sh`, `shared_script/**` path filter,
  `generate-secrets.sh`, `generate-env-files.sh`, `check-openapi-contracts.sh`)
- `infra/cdk/docs/secrets-and-config.md` lines 98, 100
- `infra/cdk/flowform_infra/stacks/security_stack.py` line 120 (comment)
- `infra/docker/docker-compose.dev.yml` lines 98, 159, 163 (comments)
- `infra/docker/docker-compose.ec2.local.yml` line 16 (comment)
- Any internal `SCRIPT_DIR`/`../..` relative paths inside the moved scripts
  themselves (`fetch-dev-secrets.sh` calls `generate-secrets.sh`;
  `bootstrap-dev-and-load-mocks.sh` calls the mock loaders).

**Method:** use `git mv` to preserve history; grep for each old path and update
references; re-run anything cheap (`ci.yml` steps locally where possible,
`bash -n` on moved scripts) to confirm nothing dangles. **Phase 0 must leave
the tree green before Phase 1 starts.**

**Verification for Phase 0:**
- `git grep -n "scripts/infra\|shared_script\|start.stop"` returns nothing
  except historical/plan references.
- `bash -n` on every moved script passes.
- `./scripts/secrets/fetch-dev-secrets.sh` still assembles dev secrets (calls
  the relocated `generate-secrets.sh` correctly).
- CI workflow YAML still references existing paths (grep the new paths exist).

---

## Phase 1 — Production bootstrap scripts (the real deliverable)

Authored under `scripts/bootstrap/`. These run on real EC2 later; the rehearsal
just exercises them. Both take a `BOOTSTRAP_ENDPOINT_URL` override (unset →
real AWS; set → LocalStack-via-proxy) as the ONLY prod-vs-rehearsal seam.

### `scripts/bootstrap/bootstrap-app.sh` (idempotent; user-data + re-run on deploy)
1. Export `HTTP_PROXY`/`HTTPS_PROXY=http://$PROXY_PRIVATE_IP:3128` and a
   `NO_PROXY` covering `localhost,127.0.0.1,169.254.169.254` + RDS suffixes
   (hostname-based — the exact caution already in `docker-compose.app.yml:39-42`:
   Python/boto3 ignore CIDR in NO_PROXY).
2. Write Docker daemon proxy drop-in
   (`/etc/systemd/system/docker.service.d/http-proxy.conf`);
   `daemon-reload && restart docker`. Daemon `no-proxy` MAY use CIDRs (Go).
3. Materialize tmpfs secrets: `/run/flowform/secrets` (tmpfs, 0700), fetch each
   via `aws secretsmanager get-secret-value` → `<NAME>.secret.txt` at 0600.
   **Reuse the JSON-key-extraction + `umask 177` pattern from
   `scripts/secrets/fetch-dev-secrets.sh` (lines 75-91)** — do not reinvent.
4. Generate `/opt/flowform/backend.env` from
   `aws ssm get-parameters-by-path /flowform/<scope>/backend/`; root-owned,
   not world-readable, **validated before swap using the
   write-to-tmp-then-`mv` pattern from `scripts/secrets/generate-env-files.sh`
   (lines 113-212)**.
5. `docker compose --env-file /opt/flowform/backend.env -f
   docker-compose.app.yml up -d`.

### `scripts/bootstrap/bootstrap-proxy.sh` (smaller sibling)
- Writes `/opt/flowform/proxy.env` from SSM, starts
  `docker-compose.proxy.yml`. **No secret materialization** — the proxy box
  holds no app secrets (checklist: "Proxy host has no app secrets").

**Verification:** `bash -n` + `shellcheck`; a dry-run mode that prints intended
file writes/perms without executing, run locally.

---

## Phase 2 — Proxmox topology + VM creation

```
Proxmox VE
  Bridges:  vmbr0  = LAN/internet
            vmbr10 = private FlowForm rehearsal net (no gateway)
  ┌ proxy-vm      NIC0 vmbr0 (internet) + NIC1 vmbr10   IP 10.10.10.10
  │    registry:2, Caddy+Squid (docker-compose.proxy.yml), TLS shim
  ├ app-vm        NIC0 vmbr10 ONLY (no default route)   IP 10.10.10.20
  │    cloud-init → bootstrap-app.sh → docker-compose.app.yml
  └ localstack-vm NIC0 vmbr10 (+optional vmbr0 seed)    IP 10.10.10.30
       LocalStack (Secrets Manager, SSM, KMS)
```

Files under `infra/rehearsal/proxmox/`:
- `create-template.sh` — build the golden cloud-init template (import Ubuntu
  cloud image, bake Docker/Compose/AWS-CLI/curl/jq/nftables, `qm template`).
- `create-vms.sh` — `qm clone` the three VMs, set NICs/bridges/IPs via
  `qm set --ipconfigN` and `--cicustom user=...`, start them. Idempotency
  guards (skip if VMID exists).
- `destroy-vms.sh` — stop + destroy the three VMs (template kept).
- `README.md` — bridge setup (`vmbr10` with no gateway), VMID conventions, how
  to run, and the **hard boundary** section (what this does NOT prove).

## Phase 3 — cloud-init user-data + rehearsal AWS/registry fixtures

Files under `infra/rehearsal/`:
- `cloud-init/app.user-data.yaml` — `write_files` drops the bootstrap scripts +
  rehearsal CA + `/etc/hosts` entries for `*.localstack.test`; `runcmd` invokes
  `bootstrap-app.sh` with `BOOTSTRAP_ENDPOINT_URL` and `PROXY_PRIVATE_IP` set.
  **This file's `write_files`/`runcmd` shape is the template for the future CDK
  `ec2.UserData`.**
- `cloud-init/proxy.user-data.yaml` — starts `registry:2`, brings up the
  LocalStack TLS shim, runs `bootstrap-proxy.sh`.
- `cloud-init/localstack.user-data.yaml` — runs LocalStack.
- `seed-localstack.sh` — `awslocal secretsmanager create-secret` /
  `ssm put-parameter` for `/flowform/<scope>/backend/*` and app-secrets. Values
  are rehearsal throwaways from `scripts/secrets/generate-secrets.sh`.
- `squid/allowed-domains.rehearsal.txt` — prod allow-list **plus**
  `*.localstack.test` + registry host. The prod
  `infra/docker/squid/allowed-domains.txt` is NOT modified.
- `tls-shim/` — stunnel or `caddy tls internal` fronting LocalStack with the
  three SNI names; generated rehearsal CA (trusted on app-vm only).
- `build-and-push-image.sh` — build the backend image, push to the proxy VM's
  `registry:2`, print the digest for `BACKEND_IMAGE`.

## Phase 4 — Assertion harness (`infra/rehearsal/verify.sh`)

Runs over SSH against app-vm/proxy-vm and FAILS loudly on regression. Encodes
the locally-provable checklist items exactly:
```
 1. app VM has NO default internet route
 2. direct `curl --max-time 5 https://example.com` FAILS
 3. `curl --proxy 10.10.10.10:3128 https://<allowed>` SUCCEEDS
 4. `curl --proxy 10.10.10.10:3128 https://<blocked>` FAILS
 5. Squid access.log shows the deny for #4
 6. Docker daemon proxy drop-in present AND active (docker info shows proxy)
 7. /opt/flowform/backend.env exists, root-owned, not world-readable
 8. /run/flowform/secrets is tmpfs; dir 0700; secret files 0600
 9. backend container running; healthcheck passes
10. `aws secretsmanager get-secret-value` from app VM via proxy→LocalStack works
11. `aws ssm get-parameters-by-path` likewise; backend.env matches seeded params
12. re-run bootstrap-app.sh → idempotent (secrets re-materialized, env re-swapped,
    compose restarted cleanly)
```

## Phase 5 — Docs

- `infra/rehearsal/README.md` — run instructions + hard-boundary section
  (does NOT prove: IMDS/hop-limit-2, real route tables, SG enforcement, S3
  gateway endpoint layer path, DNS-01, RDS isolation → pointer to the staging
  smoke-test section of the due-diligence checklist).
- Annotate `ec2-compose-due-diligence-checklist.md`: tag each locally-provable
  item "(rehearsable locally)" so it doubles as the local-vs-staging coverage
  map. Annotation only — no new claims.

---

## Overall verification

1. **Phase 0 gate:** tree green, no dangling script references, `bash -n` clean,
   `fetch-dev-secrets.sh` still works.
2. `infra/rehearsal/proxmox/create-template.sh` then `create-vms.sh` — three
   VMs boot from cloud-init.
3. `infra/rehearsal/verify.sh` — all 12 assertions pass; especially the three
   egress assertions and the tmpfs/0600 secret checks.
4. Idempotency: re-run `create-vms.sh`/bootstrap → clean re-converge.
5. Existing CDK tests unaffected: `cd infra/cdk && uv run pytest -q`.

## Explicitly NOT in this plan (stays staging-only)

No local IMDS simulation (AWS flags hop-limit 2 as a staging risk — faking it
locally misleads), no S3-gateway-endpoint layer path, no DNS-01 (Caddy uses
`tls internal` locally), no RDS SG isolation. These are the staging smoke
test's job.

## Follow-on (next milestone, not this plan)

Wire the proven `scripts/bootstrap/*` into CDK `ApplicationStack` as
`ec2.UserData.for_linux()` (the deferred `TODO` at `application_stack.py:177`),
then real-ECR pull + the staging smoke test.

## Open item deferred by request

Hooking up direct Proxmox access for the assistant (so VM creation/verify can
run without copy-paste) — worth doing later, not now.
