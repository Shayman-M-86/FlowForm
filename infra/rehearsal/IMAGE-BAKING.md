# Image baking pattern — "bake online, run offline"

The rehearsal's offline VMs (`app-vm`, `ls-vm`) must boot into a fully working
state **without any installation or download at boot** — because in the real
design the private app box has no internet route, only a forced-proxy egress to
an allow-list. So anything a VM needs at runtime has to already be present in its
template.

This doc is the **general rule** for every template we build, and a record of how
each specific image is baked.

---

## The rule

> **Bake with temporary full access, then seal the template offline.**
> A template is built once, online, with everything downloaded and initialised.
> After that it boots offline and just *runs* — no `apt install`, no `docker
> pull`, no network dependency at boot.

Concretely, every template follows the same lifecycle:

```text
1. BOOT a builder VM with TEMPORARY full internet (a vmbr0 NIC).
2. cloud-init DOWNLOADS everything it will ever need:
     - OS packages (Docker, Compose, AWS CLI, agents, tools)
     - container images (docker pull ...) → into the local image cache
     - any files/CA/config that must be present
3. cloud-init CLEANS itself (apt cache, cloud-init state, machine-id).
4. cloud-init POWERS THE VM OFF — the done-signal the host waits for.
5. The host strips the build-time NIC/user-data and runs `qm template`.
6. The template now boots OFFLINE and everything is already there.
```

Step 5 is the important discipline: the internet access is a **build-time
scaffold**, not a runtime property. Removing it before templating keeps the
offline guarantee honest — a template that still had a route would let a broken
"needs to download at boot" path pass unnoticed.

### Why this mirrors production

The real app box gets its host dependencies from a **pre-baked golden AMI** and
its application from a **container image pulled from ECR** — never from the
public internet. "Bake online, run offline" is exactly that property, rehearsed
locally. See `docs/Infrastructure/clean-up-and-VM-plan.md` (golden-image
strategy) and the `project_golden_image_strategy` memory.

---

## One baking mechanism: cloud-init self-provisioning

Every template is built the **same way** — the host script drives only the
Proxmox VM lifecycle; a cloud-init `*-builder.user-data.yaml` does all the
installing. There is no `virt-customize` (offline image editing), no
`qm guest exec`, and no SSH in the bake path.

```text
qm            = the factory robot: create/clone the VM shell, resize disk,
                attach user-data, start, poll status, convert to template.
cloud-init    = the instruction sheet the VM follows on first boot: install
                everything, clean itself, then `poweroff`.
poweroff      = the done-signal. The host just waits for the VM to reach
                'stopped' — no agent or SSH needed to observe completion.
```

Why this shape:

- **Boot-safe growth.** The disk is grown with `qm disk resize`; cloud-init's
  own `growpart` expands the root fs at first boot. (Offline `virt-resize`
  reordered GPT partitions and broke boot.)
- **No chicken-and-egg.** The bare cloud image has no `qemu-guest-agent`, so we
  can't drive the *golden* build via `qm guest exec`. cloud-init needs nothing
  pre-installed.
- **Fail-loud.** cloud-init only reaches its final `poweroff` if every `runcmd`
  succeeded. A failed step means no poweroff → the host's wait-for-stopped loop
  times out → the build fails instead of sealing a broken template.

Shared orchestration lives in `proxmox/lib/template-build.sh`
(`tb_install_snippet`, `tb_wait_stopped`, `tb_finalize_template`); the per-role
install lives in `proxmox/cloud-init/*-builder.user-data.yaml`.

---

## Templates we build (the complete set — three)

### `9000` — golden base (proxy + app clone this)

`proxmox/create-template.sh` + `cloud-init/golden-builder.user-data.yaml`:
Docker Engine + Compose plugin, **AWS CLI v2**, `qemu-guest-agent`, `curl`, `jq`,
`ca-certificates`, `unzip`, `nftables`, `/opt/flowform`. No app, no secrets, no
container images. Clones: **proxy (210)** and **app (220)** — bare, because their
role setup is the thing under test (see below).

### `9001` — ls-vm base (LocalStack)

`proxmox/create-localstack-template.sh` +
`cloud-init/localstack-builder.user-data.yaml`: clone `9000`, `docker pull
localstack/localstack:3` into the cache, seal, template. Clone: **ls-vm (230)**,
which boots fully offline with the image already present. LocalStack is fake-AWS
scaffolding, so it's baked rather than delivered through the registry.

### `9002` — dev-box base (operator workbench)

`proxmox/create-dev-template.sh` + `cloud-init/dev-builder.user-data.yaml`: clone
`9000`, add `git`, `yq`, `awslocal`, `python3-venv/pip`, etc. Clone: **dev (240)**,
an out-of-scope dual-homed workbench (see the `project_rehearsal_dev_box` memory).

### proxy / app get NO dedicated template

proxy (210) and app (220) clone the **bare golden 9000**. Their role content —
Caddy/Squid images and `proxy.env` for the proxy; the backend image, secrets, and
`backend.env` for the app — arrives at **runtime** via `bootstrap-proxy.sh` /
`bootstrap-app.sh`. That runtime setup is exactly what the rehearsal exists to
prove, so baking it into a template would defeat the point. This mirrors AWS:
golden AMI (host deps) → EC2 user-data (runtime role config) → ECR/SSM/Secrets
via private endpoints.

### backend image → private registry, NOT a template

The real backend/app image is delivered at runtime through the private registry
(`registry:2` on the proxy, `10.10.10.10:5000`) so we rehearse "offline private
box pulls an approved image from a trusted source" (locally the registry; in
prod, ECR). Pulling the app image is a thing the real bootstrap does. See
`fixtures/registry/`.

**Rule of thumb:** bake *scaffolding and host deps* into templates; deliver the
*thing under test* (role config + the app image) at runtime.

---

## Adding a new baked template later

Copy the `create-localstack-template.sh` / `create-dev-template.sh` shape:

1. Pick a new template VMID (9003, …).
2. Write a `cloud-init/<role>-builder.user-data.yaml` that installs what you need,
   cleans (`apt-get clean`, `cloud-init clean --logs`, truncate `machine-id`),
   and ends with `poweroff`.
3. In the script: `qm clone 9000 → NEW`, attach the user-data with
   `tb_install_snippet` + `--cicustom`, `qm start`, `tb_wait_stopped`,
   `tb_finalize_template`.

Keep every such script idempotent (refuse if the VMID exists; `--force`
rebuilds).
