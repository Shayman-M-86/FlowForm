# Proxmox rehearsal — topology & VM lifecycle

Scripts that stand up the **local Proxmox rehearsal** for the FlowForm split-EC2
runtime. They prove the *bootstrap mechanics* on real VMs before we spend time on
real EC2. Run them **on the Proxmox host** (`root@192.168.68.88`).

> **Template philosophy — "bake online, run offline":** every template is built
> once with temporary full internet, has everything downloaded/initialised, then
> is sealed so it boots offline with nothing left to fetch. See
> [`../IMAGE-BAKING.md`](../IMAGE-BAKING.md).

## What this proves — and what it deliberately does NOT

```
Local Proxmox VMs  = prove BOOTSTRAP MECHANICS (real systemd, real Docker daemon
                     config, real two-NIC routing, real tmpfs, forced-proxy egress).
Staging EC2        = prove the AWS TRUST BOUNDARY (IMDSv2 + hop-limit 2, real route
                     tables, SG enforcement, S3 gateway endpoint for ECR layers,
                     Route 53 DNS-01, RDS SG isolation).
```

Do **not** read a green rehearsal as AWS proof. The trust-boundary items above are
the staging smoke test's job — see the due-diligence checklist.

## Topology

```
Proxmox VE (192.168.68.88)
  Bridges:  vmbr0  = LAN/internet (pre-existing)
            vmbr10 = private rehearsal net, NO uplink, NO gateway
  ┌ proxy-vm  (210)  NIC0 vmbr0 (DHCP) + NIC1 vmbr10   10.10.10.10  — HAS internet
  │    cloud-init → registry:2 + bootstrap-proxy.sh → Caddy (tls internal) + Squid
  │    (rehearsal allow-list: *.localstack.test). Egress gateway for the app box.
  ├ app-vm    (220)  NIC0 vmbr10 ONLY, NO gateway      10.10.10.20  — NO internet
  │    cloud-init → bootstrap-app.sh → docker-compose.app.yml
  ├ ls-vm     (230)  NIC0 vmbr10 ONLY                  10.10.10.30  — private only
  │    LocalStack (Secrets Manager, SSM, KMS) + TLS shim (*.localstack.test:443)
  └ dev-vm    (240)  NIC0 vmbr0 (static .100) + vmbr10 10.10.10.40  — OUT OF SCOPE
       operator workbench (awscli/awslocal/git); toggle off for clean runs
```

The app box's isolation is **structural**: its only NIC is on `vmbr10` (no uplink,
no gateway) and its cloud-init sets no gateway — so it cannot route off the private
net. Verified: `curl https://1.1.1.1` from 220 → `000`/FAILED; from 210 → `301`.

## VMID conventions

Templates (never started, only cloned):

| VMID | Template | Contents |
|---|---|---|
| 9000 | golden | host deps: Docker + Compose, AWS CLI, qemu-guest-agent, base tools |
| 9001 | ls-vm | 9000 + LocalStack image + TLS shim (Caddy) + auto-start systemd units |
| 9002 | dev | 9000 + operator extras (git, yq, awslocal, ~/.aws → LocalStack) |

VMs:

| VMID | Role | Clones | Notes |
|---|---|---|---|
| 210  | proxy-vm | 9000 | dual-homed; egress gateway; role config from bootstrap at runtime |
| 220  | app-vm | 9000 | private only; offline by construction; the box under test |
| 230  | ls-vm | 9001 | private only; LocalStack + TLS shim auto-start on boot |
| 240  | dev-vm | 9002 | out-of-scope workbench; static LAN `192.168.68.100`; `WITH_DEV_BOX=1`; builds+pushes the backend image (trusts the private registry) |
| 100  | (yours) | — | pre-existing "Ubuntu" VM — untouched by these scripts |

## Run order

```sh
# 0. Host prep (bridge + snippets). Idempotent; --undo reverts.
./setup-host.sh

# 1. Templates — each boots a builder VM that self-provisions via cloud-init,
#    cleans, powers off; the script waits for 'stopped' then `qm template`.
#    --force rebuilds. (See ../IMAGE-BAKING.md for the pattern.)
./create-template.sh              # 9000 golden
./create-localstack-template.sh   # 9001 ls-vm (clones 9000)
./create-dev-template.sh          # 9002 dev  (clones 9000)

# 2. Clone + start the VMs. Idempotent (skips existing); --force reclones.
#    Renders the app + proxy cloud-init from the real repo files first, then
#    attaches them via --cicustom. WITH_DEV_BOX=1 also creates the workbench (240).
#      proxy (210): registry:2 + Caddy(tls-internal) + Squid(rehearsal allow-list)
#      app   (220): trust CA, /etc/hosts, insecure-registry, run bootstrap-app.sh
WITH_DEV_BOX=1 ./create-vms.sh

# ...rehearse:
#    - build + push the backend image  ../fixtures/registry/build-and-push-backend.sh
#         (on the DEV BOX 240 — needs the repo synced there; pushes to 10.10.10.10:5000)
#    - seed the private registry        ../fixtures/registry/seed-registry.sh   (on 210)
#    - seed LocalStack                  ../fixtures/localstack/seed-localstack.sh (dev box)
#    - then Phase 4 verify.sh...
#
# The app box (220) pulls BACKEND_IMAGE=10.10.10.10:5000/flowform-backend:rehearsal
# at bootstrap, so the image must be pushed BEFORE 220's bootstrap compose-up
# succeeds (re-run bootstrap-app.sh on 220 after pushing if it raced ahead).

# 3. Tear the VMs down (templates + bridges kept).
./destroy-vms.sh
```

## Access

- **Dev box (workbench):** `ssh -i ~/.ssh/proxmox_codex flowform@192.168.68.100`
  (static LAN IP). Has `aws`/`awslocal` preconfigured for LocalStack. Add `-A`
  (agent forwarding) to hop onward to the private VMs.
- **proxy-vm (210):** on the LAN via DHCP — find its IP with
  `qm guest cmd 210 network-get-interfaces`, then `ssh flowform@<ip>`.
- **The app/ls VMs are NOT on the LAN** — reach them from the dev box (or proxy)
  with agent forwarding: `ssh -A flowform@10.10.10.20` (app), `10.10.10.30` (ls).
  Your Proxmox host SSH key is injected into all clones by `create-vms.sh`.
- **From the host directly:** `qm terminal <vmid>` for a serial console. (Note:
  `qm guest exec` works but is flaky for scripted use — prefer SSH via the dev box.)

## Prerequisites / gotchas

- **Backend image staging (dev box).** The dev box (240) builds + pushes the
  backend image to the private registry (`build-and-push-backend.sh`). It needs
  the repo synced there (it has `git` + internet — `git clone` or `rsync`), and
  its template (9002) bakes `insecure-registries: 10.10.10.10:5000` so the push
  works. If you built 9002 before that was added, rebuild it:
  `./create-dev-template.sh --force`.
- **App box image-pull ordering.** 220 boots and runs `bootstrap-app.sh` before
  the operator pushes the image, so its first compose-up fails to pull — expected.
  Push the image (dev box), then re-run `/opt/flowform/scripts/run-bootstrap-app.sh`
  on 220 (SSH via dev box). The bootstrap is idempotent.
- **Host virtualization must be enabled.** If `qm start` fails with *"KVM
  virtualisation configured, but not available"*, enable **SVM** (AMD) / **VT-x**
  (Intel) in the host BIOS and reboot — `dmesg | grep -i 'disabled by BIOS'`
  confirms. `/dev/kvm` must exist.
- `setup-host.sh` must run first — every `create-*` script needs `snippets`
  content on `local` (for cloud-init builder user-data), and `create-vms.sh`
  fails closed if `vmbr10` is missing.
- Template disks live on `ZFS-RAIDZ`; clones are full clones on the same pool.
- The scripts reference sibling `cloud-init/` + `lib/` files, so run them from a
  synced copy on the host, not piped over stdin. **Sync from the REPO ROOT**, not
  just `infra/rehearsal/` — `create-vms.sh` renders the app user-data from
  `infra/scripts/bootstrap/bootstrap-app.sh` and `infra/docker/docker-compose.app.yml`,
  which live *outside* `infra/rehearsal/`. E.g. `rsync -a --relative
  infra/{rehearsal,scripts/bootstrap,docker} root@host:/root/flowform/` then run
  from `/root/flowform/infra/rehearsal/proxmox/`. (Or set `REPO_ROOT=` to point
  the render script at the sources explicitly.)

## Files

| Script | Does | Reversible |
|---|---|---|
| `setup-host.sh` | create `vmbr10`, enable `snippets` on `local` | `--undo` |
| `create-template.sh` | build golden template 9000 (cloud-init self-provision) | `--force` rebuilds |
| `create-localstack-template.sh` | build ls-vm template 9001 (LocalStack + TLS shim) | `--force` rebuilds |
| `create-dev-template.sh` | build dev template 9002 (operator extras) | `--force` rebuilds |
| `create-vms.sh` | clone + configure + start 210/220/230 (+240 if `WITH_DEV_BOX=1`) | `--force` reclones |
| `destroy-vms.sh` | stop + destroy 210/220/230/240 (templates kept) | n/a |
| `cloud-init/*-builder.user-data.yaml` | per-template self-provision instructions | — |
| `cloud-init/app.user-data.yaml.template` | app-box (220) cloud-init: trust CA, `/etc/hosts`, insecure-registry, run `bootstrap-app.sh` | — |
| `cloud-init/proxy.user-data.yaml.template` | proxy-box (210) cloud-init: trust CA, registry:2, run `bootstrap-proxy.sh` (Caddy tls-internal + Squid rehearsal allow-list) | — |
| `cloud-init/render-user-data.sh` | renders every `*.template` → `.rendered.yaml` by injecting the real repo files (single source of truth) | idempotent |
| `lib/template-build.sh` | shared build helpers (install snippet, wait-stopped, finalize) | — |
