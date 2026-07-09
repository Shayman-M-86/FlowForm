# Plan: Script Reorg + Proxmox Local Bootstrap Rehearsal Harness

> Living execution plan. **Phase 0 and Phase 1 are DONE** (see status below).
> Phases 2–5 build a Proxmox-hosted rehearsal that boots clean Linux VMs into
> the locked-down split-EC2 runtime, driven **step-by-step with the user in the
> loop** for every Proxmox-host action.

---

## Status at a glance

| Phase | What | State |
|---|---|---|
| 0 | Script reorganization | ✅ done |
| 1 | Production bootstrap scripts (`infra/scripts/bootstrap/`) | ✅ done |
| 2 | Proxmox topology + VM creation | ⏳ next — step-by-step |
| 3 | cloud-init user-data + LocalStack/registry/TLS-shim fixtures | ⏳ |
| 4 | `verify.sh` assertion harness | ⏳ |
| 5 | Docs (rehearsal README + checklist annotation) | ⏳ |

---

## Context / Why

The split-EC2 runtime (public **proxy box**: Caddy + Squid; private **app box**:
backend only) is fully described in CDK, and both production Compose files
exist and are hardened:
- `infra/docker/docker-compose.proxy.yml` (Caddy + Squid)
- `infra/docker/docker-compose.app.yml` (backend only)

But the CDK `ApplicationStack` boots instances into **nothing** — there is a
`TODO: host bootstrap is intentionally deferred` at
`infra/cdk/flowform_infra/stacks/application_stack.py`. Everything the runtime
depends on at first boot is unproven: the bootstrap/user-data script, the Docker
daemon proxy drop-in, env-file generation, tmpfs secret materialization, and
forced-proxy egress. The project's own due-diligence checklist
(`infra/cdk/docs/implementation-sketch/ec2-compose-due-diligence-checklist.md`)
concentrates the remaining risk in exactly these host-bootstrap items.

**Goal:** rehearse the from-clean-boot bootstrap on **real VMs on Proxmox**,
driven by **cloud-init** (the exact artifact EC2 consumes). The bootstrap
scripts are the real production deliverable; the Proxmox harness exercises them
from a clean machine before we spend money/time on real EC2.

**Held boundary — do not blur it:**

```text
Local Proxmox VMs = prove BOOTSTRAP MECHANICS (real systemd, real Docker
                    daemon config, real two-NIC routing, real tmpfs, real
                    forced-proxy egress).
Staging EC2       = prove the AWS TRUST BOUNDARY (IMDS + hop-limit 2, real
                    route tables, SG enforcement, S3 gateway endpoint for ECR
                    layers, Route 53 DNS-01, RDS SG isolation).
```

## Confirmed decisions

- **Host platform: Proxmox VE 9.1.6** at `192.168.68.88`. Real Linux bridges
  give genuine network isolation; LocalStack is just another VM on the private
  net.
- **Assistant has SSH access:** `ssh -i ~/.ssh/proxmox_codex root@192.168.68.88`.
  The assistant drives `qm`/host commands directly, **but every Proxmox-host
  mutation (bridge creation, VM create/destroy/start) is proposed and run with
  the user watching, one step at a time** — the user explicitly wants to be in
  the loop. Read-only surveys can run freely.
- **First boot: cloud-init** on an Ubuntu cloud image; bootstrap authored as
  real user-data, reusable later as CDK `ec2.UserData.for_linux()`.
- **VM creation: `qm` shell scripts** (clone from a cloud-init template).
  Structured so an OpenTofu wrapper can adopt them later without rework.
- **Golden image strategy — pre-baked, not boot-time installs** (decided
  2026-07-09). Production EC2 hosts launch from a **pre-baked golden image**;
  the local Proxmox template mirrors it. This is an image *strategy*, not a tool
  commitment — the AWS builder (Packer vs EC2 Image Builder) is left open. The
  app box has no package-mirror route, so apt-installing Docker at boot would
  need a temporary broad-egress window prod must never have; baking is the only
  honest option and gives exact local↔cloud parity (`qm template` ≙ future AMI).

  **Strict layering (what goes where):**

  | Layer | Contents |
  |---|---|
  | Golden image / template | host deps ONLY — Docker, Compose plugin, guest/mgmt agents (qemu-guest-agent local; SSM Agent + CloudWatch Agent on EC2), base tools (curl, jq, ca-certificates, unzip), cloud-init, nftables, hardening, `/opt/flowform` |
  | Docker image | the app — Python, uv, Flask, app deps |
  | Runtime (cloud-init + bootstrap) | secrets + env config — tmpfs secrets, `backend.env` from SSM, image tag/digest |

  **Never baked:** `.env` files, DB passwords, Auth0 secrets, AWS keys, SSH
  keys, any env-specific config or mutable app data.

  **FlowForm-specific vs generic golden-image advice:** we do **not** use
  interface VPC endpoints (secretsmanager/kms/ssm/logs interface endpoints,
  ~$7.5/mo each — all rejected). The private app box reaches AWS *through Squid*
  (forced-proxy egress) plus the free **S3 gateway endpoint** for ECR layers
  (ECR needs ECR API access for the manifest + S3 for layers). Prefer SSM
  Session Manager over SSH for EC2 admin (no inbound ports). This is the reason
  the local rehearsal fronts LocalStack with a TLS shim so app-box AWS calls
  ride Squid.

  **Local bake mechanics (decided 2026-07-09, revised):** ALL templates build via
  **cloud-init self-provisioning** — one uniform pattern. The host script drives
  only the `qm` lifecycle (create/clone → resize disk → attach a
  `*-builder.user-data.yaml` via `--cicustom` → boot → wait for `stopped` →
  `qm template`); the builder user-data installs everything, cleans, then
  `poweroff` (the poweroff is the host-observable done-signal). No `virt-customize`
  (offline editing broke boot via GPT partition reorder), no `qm guest exec` (bare
  cloud image has no agent — chicken-and-egg), no SSH. Disk grown by `qm disk
  resize` + cloud-init growpart (boot-safe). Shared orchestration in
  `proxmox/lib/template-build.sh`; user-data in `proxmox/cloud-init/`. Template
  disk on **`ZFS-RAIDZ`**; snippets on `local`. **Three templates only:** 9000
  golden (host deps incl. AWS CLI), 9001 ls-vm (localstack pre-pulled), 9002 dev
  (operator extras). proxy(210)/app(220) clone bare 9000 — role setup is the
  thing under test, done at runtime by the bootstrap scripts. See
  `infra/rehearsal/IMAGE-BAKING.md`.
- **Fake AWS: LocalStack** (Secrets Manager, SSM, KMS) on its own VM. Bootstrap
  runs *real* `aws` CLI calls against it via `BOOTSTRAP_ENDPOINT_URL`, so the
  AWS code path is exercised, not stubbed.
- **Fake registry: `registry:2`** on the proxy VM for `BACKEND_IMAGE`.

### Discovered host facts (survey, this session)

- Bridges: `vmbr0` (LAN uplink) + **`vmbr10` created 2026-07-09** by
  `setup-host.sh` (private, no ports, no gateway). `vmbr0` and VM 100 untouched.
- Storage: `local-lvm` (lvmthin, empty — VM disks), `local` (dir — ISOs,
  snippets/cloud-init user-data; **`snippets` content enabled 2026-07-09**),
  `ZFS-RAIDZ` (large, spare — **holds the template disk**). `synology` NFS is
  offline — ignore.
- Existing VM 100 "Ubuntu" (stopped) — avoid that ID. Use template **9000**
  (confirmed free) and VMs **210** (proxy) / **220** (app) / **230**
  (localstack).
- Host tooling: `qm`, `wget`, `qemu-img` present. (No `libguestfs`/`virt-*`
  needed — templates self-provision via cloud-init, not offline image editing.)

## Repository organization for the rehearsal

Decided: **minimal reorg** — leave `infra/docker/`, `infra/cdk/`,
`infra/postgres/`, `infra/scripts/` exactly as they are (the `.dev`/`.app`/
`.proxy` compose suffixes already signal local-vs-cloud). Add only one new
tree:

```text
infra/rehearsal/          # local-Proxmox-ONLY, disposable
  proxmox/     create-template.sh, create-vms.sh, destroy-vms.sh, README.md
  cloud-init/  app.user-data.yaml, proxy.user-data.yaml, localstack.user-data.yaml
  fixtures/    seed-localstack.sh, build-and-push-image.sh
  tls-shim/    LocalStack SNI terminator config + rehearsal CA
  squid/       allowed-domains.rehearsal.txt
  verify.sh
  README.md
```

**The rule that keeps it clean:** everything under `infra/rehearsal/` is
local-only and disposable. Anything it needs that is ALSO a real production
artifact — the compose stacks (`infra/docker/docker-compose.{app,proxy}.yml`),
the bootstrap scripts (`infra/scripts/bootstrap/*`), `Caddyfile.proxy`,
`squid.conf` — it **references by path, never copies**. Deleting
`infra/rehearsal/` must leave production completely unaffected; that is the
test of whether a file belongs there. Dependency direction is one-way:
`rehearsal/` → `infra/scripts/bootstrap/` → `infra/docker/*compose*`. Nothing
production depends back down into `rehearsal/`.

## Fidelity constraint to keep honest

Squid allows `CONNECT` only to **443** and allow-lists by **TLS SNI**
(`infra/docker/squid/squid.conf`). LocalStack serves plain HTTP on `:4566`. To
keep "app-box AWS calls ride Squid" TRUE (routing-enforced: the app VM has no
route to LocalStack except via the proxy), front LocalStack with a **TLS
terminator presenting SNI names** in a rehearsal allow-list
(`secretsmanager.localstack.test`, `ssm.localstack.test`, `kms.localstack.test`),
`/etc/hosts` on the app VM resolving them to the LocalStack VM IP, and Squid's
rehearsal allow-list admitting them. The app box then does exactly what prod
does: `CONNECT <host>:443` → Squid → allow → TLS tunnel. The only deltas from
prod are the hostnames and a rehearsal-only CA — documented in the README so it
is never mistaken for AWS proof.

---

## Phase 0 — Script reorganization ✅ DONE

Scripts were scattered and mixed by concern (a dir literally named
`start.stop  ` with trailing spaces; secret plumbing mixed with mock-data
loaders). Final layout, split "runs on a laptop / in CI" from "runs on a
server":

```text
scripts/                      # developer + CI workflow (repo root)
  dev/       install-git-hooks.sh, bootstrap-dev-and-load-mocks.sh,
             load-core-mock-data.sh, load-response-mock-data.sh
  secrets/   fetch-dev-secrets.sh, generate-secrets.sh, generate_secrets.py,
             generate-env-files.sh
  ci/        check-openapi-contracts.sh, sync-openapi.sh   (was shared_script/)
  tools/     count_lines.sh, lint-md.sh
  backend/   run_backend_security.sh

infra/scripts/                # infra / deployment operations (runs on a server)
  bootstrap/ bootstrap-app.sh, bootstrap-proxy.sh          (Phase 1)
  cdk/       seed-secrets.sh
```

Done via `git mv` (history preserved as renames). All references swept in
`.github/workflows/ci.yml`, `.githooks/pre-commit`, `docs/test-suite.md`,
`.claude/rules/frontend-codegen.md`, the wire-api skills, CDK comments, and the
compose files. Verified: `git grep` for old paths is clean, `bash -n` passes on
all scripts, `fetch-dev-secrets.sh` still resolves its sibling call, 27 CDK
tests green.

> Note: the bootstrap scripts landed in **`infra/scripts/bootstrap/`** (beside
> `infra/scripts/cdk/`), not the `scripts/bootstrap/` shown in the original
> draft — they run on servers, so they belong with infra ops, fully out of the
> root `scripts/` tree.

---

## Phase 1 — Production bootstrap scripts ✅ DONE

`infra/scripts/bootstrap/bootstrap-app.sh` and `bootstrap-proxy.sh`. Both are
idempotent, fail-closed, and have a `BOOTSTRAP_DRY_RUN=1` mode. The single
prod-vs-rehearsal seam is `BOOTSTRAP_ENDPOINT_URL` (unset → real AWS; set →
LocalStack via proxy).

**`bootstrap-app.sh`** (private app box):
1. Export `HTTP_PROXY`/`HTTPS_PROXY=http://$PROXY_PRIVATE_IP:3128`; `NO_PROXY`
   covers `localhost,127.0.0.1,169.254.169.254,.rds.amazonaws.com`
   (hostname-based — Python/boto3 ignore CIDR in NO_PROXY).
2. Write Docker daemon proxy drop-in
   (`/etc/systemd/system/docker.service.d/http-proxy.conf`), daemon-reload +
   restart. Daemon `no-proxy` uses CIDRs (Go).
3. Materialize tmpfs secrets: `/run/flowform/secrets` (tmpfs, 0700), four files
   at 0600 from `flowform/<scope>/{app,db}-secrets` — reuses the
   JSON-key + `umask 177` pattern from `scripts/secrets/fetch-dev-secrets.sh`.
4. Render `/opt/flowform/backend.env` (0600) from
   `aws ssm get-parameters-by-path /flowform/<scope>/backend/` +
   injected `APP_PRIVATE_IP`/`PROXY_PRIVATE_IP`/proxy vars; validate-to-tmp-then-`mv`
   like `scripts/secrets/generate-env-files.sh`; fails closed if no `BACKEND_IMAGE`.
5. `docker compose --env-file /opt/flowform/backend.env -f docker-compose.app.yml up -d`.

**`bootstrap-proxy.sh`** (public proxy box): renders `/opt/flowform/proxy.env`
from `/flowform/<scope>/proxy/*` + host-known IPs (incl.
`SQUID_APP_SOURCE_CIDR=<APP_PRIVATE_IP>/32`), starts `docker-compose.proxy.yml`.
**No secret materialization** — the proxy box holds no app secrets.

Verified: `bash -n` clean; dry-run exercised locally (correct output, zero
side effects, compose-file path resolves three-up from
`infra/scripts/bootstrap/`).

> **Contract the bootstrap defines that CDK does not fulfil yet:** it reads
> config from SSM `/flowform/<scope>/backend/*` and `/flowform/<scope>/proxy/*`.
> Those param paths don't exist in CDK (the app-stack TODO). The rehearsal
> seeds them into LocalStack, so the scripts are exercised; **CDK creating them
> for real is follow-on work.**

---

## Phase 2 — Proxmox topology + VM creation (⏳ step-by-step)

Target topology:

```text
Proxmox VE (192.168.68.88)
  Bridges:  vmbr0  = LAN/internet (exists)
            vmbr10 = private FlowForm rehearsal net, NO gateway (to create)
  ┌ proxy-vm  (VMID 210)  NIC0 vmbr0 + NIC1 vmbr10   IP 10.10.10.10
  │    registry:2, Caddy+Squid (docker-compose.proxy.yml), LocalStack TLS shim
  ├ app-vm    (VMID 220)  NIC0 vmbr10 ONLY (no default route)  IP 10.10.10.20
  │    cloud-init → bootstrap-app.sh → docker-compose.app.yml
  └ ls-vm     (VMID 230)  NIC0 vmbr10               IP 10.10.10.30
       LocalStack (Secrets Manager, SSM, KMS)
```

**Step-by-step (each host mutation proposed, then run with the user):**

1. ✅ **DONE 2026-07-09** — `setup-host.sh` created `vmbr10` (private, no ports,
   no gateway) and enabled `snippets` content on `local`. Read-back confirmed;
   `vmbr0` and VM 100 untouched. Reversible via `setup-host.sh --undo`.
2. ✅ **DONE 2026-07-09** — Three templates built via the uniform **cloud-init
   self-provision** pattern (host drives `qm` lifecycle; builder user-data
   installs + cleans + `poweroff`; host waits for `stopped` → `qm template`).
   Verified: 9000 golden has Docker 29.6.1 + Compose v5.3.1 + AWS CLI 2.35.19 +
   qemu-guest-agent, root fs 15G; 9001 has localstack pre-pulled; 9002 has
   git/yq/awslocal. All on `ZFS-RAIDZ`.
   - `create-template.sh` + `cloud-init/golden-builder.user-data.yaml` → **9000**
   - `create-localstack-template.sh` + `cloud-init/localstack-builder…` → **9001**
   - `create-dev-template.sh` + `cloud-init/dev-builder…` → **9002**
   - Shared orchestration: `proxmox/lib/template-build.sh`.
   (Earlier `virt-customize`/`virt-resize` attempt abandoned — offline partition
   reorder broke boot; guest-exec hit the no-agent chicken-and-egg + `qm shutdown`
   hangs. cloud-init avoids all three.) Each script `--force` rebuilds; refuses if
   the VMID exists.
   Golden builder also drops `/etc/cloud/cloud.cfg.d/99-flowform-no-apt.cfg`
   (`package_update/upgrade: false`, `preserve_sources_list`) so CLONES don't run
   cloud-init's default apt refresh at boot — the offline app/ls boxes otherwise
   wasted ~3.5min hammering DNS timeouts against unreachable mirrors. After the
   fix the app box reaches its guest agent in ~1s with zero apt-fetch errors.
3. **Create + start the three VMs** — `create-vms.sh` + `destroy-vms.sh`
   (written, syntax-clean). Static IPs via cloud-init ipconfig (no DHCP on the
   private net); app-vm gets NO gateway → structurally offline. Host SSH keys
   injected into clones. Idempotent (skip existing; `--force` reclones).

   ✅ **DONE 2026-07-09.** (Was briefly blocked by host BIOS: `SVM disabled (by
   BIOS) in MSR_VM_CR` → no `/dev/kvm`. Resolved by enabling **SVM Mode** in
   BIOS + reboot; `/dev/kvm` + `kvm_amd` now present, nested virt on.) All three
   VMs run: 210 proxy (`192.168.68.75` LAN + `10.10.10.10` priv), 220 app
   (`10.10.10.20` priv ONLY), 230 localstack (`10.10.10.30` priv ONLY).
   **Isolation verified via guest agent:** app-vm 220 has NO default route and
   `curl https://1.1.1.1` → `000`/FAILED; proxy-vm 210 has a default route and
   reaches the internet (`301`). The core "app box is structurally offline"
   property is proven on real VMs.
4. `README.md` under `infra/rehearsal/proxmox/` — bridge setup, VMID
   conventions, run order, and the hard-boundary section.

## Phase 3 — cloud-init user-data + rehearsal fixtures (⏳)

**Progress 2026-07-09:**
- ✅ **Template baking pattern generalised** — `infra/rehearsal/IMAGE-BAKING.md`
  documents "bake online, run offline": every template built once with temporary
  full internet, everything downloaded/initialised, temp NIC stripped, then
  `qm template`. Rule of thumb: bake scaffolding + host deps into templates;
  deliver the thing-under-test (app image) at runtime via the registry.
- ✅ **ls-vm template 9001** — `create-localstack-template.sh` clones 9000, temp
  internet, `docker pull localstack/localstack:3` (2.08GB), seals offline.
  `create-vms.sh` now clones 230 from 9001 (via `LS_TEMPLATE_VMID`); 210/220 stay
  on 9000.
- ✅ **LocalStack fixture proven** — `fixtures/localstack/docker-compose.localstack.yml`
  (binds `10.10.10.30:4566`, services=secretsmanager,ssm,kms). 230 boots FULLY
  OFFLINE (`curl 1.1.1.1 → 000`) and starts LocalStack from the baked image with
  zero network fetch; health shows secretsmanager/ssm/kms/sts **available**.
- ✅ **Private registry fixture** — `fixtures/registry/` (registry:2 on proxy
  10.10.10.10:5000, `seed-registry.sh`). Up and reachable; reserved for the
  backend image path. NOTE: consuming daemons need `insecure-registries` in
  daemon.json (plain HTTP on the private net) — to be set via cloud-init.
- ✅ **LocalStack auto-start** — `localstack-builder.user-data.yaml` bakes a
  `flowform-localstack.service` (systemd oneshot, `docker compose up`) + the
  compose file into template 9001, enabled for the clone's boot. Verified: fresh
  230 auto-starts LocalStack, healthy in ~36s, no manual step.
- ✅ **`seed-localstack.sh`** (`fixtures/localstack/`) — seeds EXACTLY the bootstrap
  contract (traced from bootstrap-app/proxy): SM `app-secrets`
  {app_secret_key,auth0_mgmt_secret} + `db-secrets` {db_core/response_app_password};
  SSM `/flowform/nonprod/backend/*` (log config, FLOWFORM_ENV, BACKEND_IMAGE) and
  `/proxy/*` (CADDY_IMAGE, API_DOMAIN). Throwaway values; create-or-update
  idempotent; re-run after each ls-vm reboot (PERSISTENCE=0). Proven: seeded from
  the dev box, read back with plain `aws`.
- ✅ **Dev box** static `192.168.68.100` + baked `~/.aws/{config,credentials}`
  (plain `aws` → LocalStack, no flags). `ssh flowform@192.168.68.100`.
- ✅ **TLS shim** (`tls-shim/`, baked into 9001) — Caddy on the ls-vm terminates
  TLS on :443 for `secretsmanager/ssm/kms.localstack.test`, reverse-proxies to
  LocalStack `10.10.10.30:4566`. Pre-generated **rehearsal CA** (`tls-shim/ca/`,
  throwaway) signs the SNI cert; app box trusts `rehearsal-ca.crt` (no fetch-from-
  shim chicken-and-egg). systemd unit `flowform-tls-shim.service` auto-starts it
  after LocalStack. **Proven from the dev box:** `aws --endpoint-url
  https://ssm.localstack.test ...` and `https://secretsmanager.localstack.test`
  return the seeded values over HTTPS; cert validates against the rehearsal CA
  (`Verify return code: 0`). (Gotcha fixed: Caddy must proxy `10.10.10.30:4566`,
  not `127.0.0.1` — LocalStack binds the private NIC.)
- ⏳ Remaining: app box (trust rehearsal CA + `/etc/hosts` `*.localstack.test` →
  10.10.10.30 + `~/.aws` HTTPS endpoints), rehearsal squid allow-list incl.
  `*.localstack.test`, cloud-init bootstrap user-data for proxy/app.

Files under `infra/rehearsal/`:
- `cloud-init/app.user-data.yaml` — `write_files` drops the bootstrap scripts +
  rehearsal CA + `/etc/hosts` for `*.localstack.test`; `runcmd` runs
  `bootstrap-app.sh` with `BOOTSTRAP_ENDPOINT_URL`/`PROXY_PRIVATE_IP` set.
  **This file's shape is the template for the future CDK `ec2.UserData`.**
- `cloud-init/proxy.user-data.yaml` — `registry:2`, LocalStack TLS shim, runs
  `bootstrap-proxy.sh`.
- `cloud-init/localstack.user-data.yaml` — runs LocalStack.
- `seed-localstack.sh` — `awslocal secretsmanager create-secret` / `ssm
  put-parameter` for `/flowform/<scope>/{backend,proxy}/*` and the app/db
  secrets. Values are throwaways from `scripts/secrets/generate-secrets.sh`.
- `squid/allowed-domains.rehearsal.txt` — prod allow-list **plus**
  `*.localstack.test` + registry host. Prod
  `infra/docker/squid/allowed-domains.txt` is NOT modified.
- `tls-shim/` — stunnel or `caddy tls internal` fronting LocalStack with the
  three SNI names; generated rehearsal CA (trusted on app-vm only).
- `build-and-push-image.sh` — build the backend image, push to the proxy VM's
  `registry:2`, print the digest for `BACKEND_IMAGE`.

## Phase 4 — Assertion harness `infra/rehearsal/verify.sh` (⏳)

Runs over SSH against the VMs and FAILS loudly on regression:

```text
 1. app VM has NO default internet route
 2. direct  curl --max-time 5 https://example.com                 FAILS
 3. proxied curl --proxy 10.10.10.10:3128 https://<allowed>       SUCCEEDS
 4. proxied curl --proxy 10.10.10.10:3128 https://<blocked>       FAILS
 5. Squid access.log shows the deny for #4
 6. Docker daemon proxy drop-in present AND active (docker info)
 7. /opt/flowform/backend.env exists, root-owned, not world-readable
 8. /run/flowform/secrets is tmpfs; dir 0700; secret files 0600
 9. backend container running; healthcheck passes
10. aws secretsmanager get-secret-value from app VM via proxy→LocalStack works
11. aws ssm get-parameters-by-path likewise; backend.env matches seeded params
12. re-run bootstrap-app.sh → idempotent (re-materialize, re-swap, restart clean)
```

## Phase 5 — Docs (⏳)

- `infra/rehearsal/README.md` — run instructions + hard-boundary section (does
  NOT prove: IMDS/hop-limit-2, real route tables, SG enforcement, S3 gateway
  endpoint layer path, DNS-01, RDS isolation → pointer to the staging
  smoke-test section of the due-diligence checklist).
- Annotate `ec2-compose-due-diligence-checklist.md`: tag each locally-provable
  item "(rehearsable locally)" so it doubles as the local-vs-staging coverage
  map. Annotation only — no new claims.

---

## Overall verification

1. Phase 0 gate — done (green).
2. Phase 1 — done (dry-run proven; real run happens on the app VM in Phase 3–4).
3. `vmbr10` up; template 9000 built; VMs 210/220/230 boot from cloud-init.
4. `verify.sh` — all 12 assertions pass; especially the three egress assertions
   and the tmpfs/0600 secret checks.
5. Idempotency: re-run bootstrap → clean re-converge.
6. Existing CDK tests unaffected: `cd infra/cdk && uv run pytest -q`.

## Explicitly NOT in this plan (stays staging-only)

No local IMDS simulation (AWS flags hop-limit 2 as a staging risk — faking it
locally misleads), no S3-gateway-endpoint layer path, no DNS-01 (Caddy uses
`tls internal` locally), no RDS SG isolation. These are the staging smoke
test's job.

## Follow-on (next milestone, not this plan)

- Create the SSM `/flowform/<scope>/{backend,proxy}/*` param paths in CDK
  (the contract the bootstrap already consumes).
- Wire the proven `infra/scripts/bootstrap/*` into CDK `ApplicationStack` as
  `ec2.UserData.for_linux()` (the deferred app-stack TODO).
- Real-ECR pull + the staging smoke test.
