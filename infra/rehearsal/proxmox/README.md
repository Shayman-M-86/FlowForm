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
  │    registry:2, Caddy+Squid, LocalStack TLS shim. The jump host onto vmbr10.
  ├ app-vm    (220)  NIC0 vmbr10 ONLY, NO gateway      10.10.10.20  — NO internet
  │    cloud-init → bootstrap-app.sh → docker-compose.app.yml
  └ ls-vm     (230)  NIC0 vmbr10 ONLY                  10.10.10.30  — private only
       LocalStack (Secrets Manager, SSM, KMS)
```

The app box's isolation is **structural**: its only NIC is on `vmbr10` (no uplink,
no gateway) and its cloud-init sets no gateway — so it cannot route off the private
net. Verified: `curl https://1.1.1.1` from 220 → `000`/FAILED; from 210 → `301`.

## VMID conventions

| VMID | Role | Notes |
|---|---|---|
| 9000 | golden template | baked host deps; never started, only cloned |
| 210  | proxy-vm | dual-homed; SSH here from the LAN, then hop to 220/230 |
| 220  | app-vm | private only; offline by construction |
| 230  | ls-vm  | private only; LocalStack |
| 100  | (yours) | pre-existing "Ubuntu" VM — untouched by these scripts |

## Run order

```sh
# 0. Host prep (bridge + snippets). Idempotent; --undo reverts.
./setup-host.sh

# 1. Golden template (VMID 9000). Bakes Docker/Compose/agent/tools offline via
#    virt-customize. --force rebuilds. Installs libguestfs-tools on first run.
./create-template.sh

# 2. Clone + start the three VMs. Idempotent (skips existing); --force reclones.
./create-vms.sh

# ...rehearse (Phase 3 cloud-init + fixtures, Phase 4 verify.sh)...

# 3. Tear the VMs down (template + bridges kept).
./destroy-vms.sh
```

## Access

- **From the LAN:** `ssh flowform@192.168.68.75` (proxy's DHCP address; check with
  `qm guest cmd 210 network-get-interfaces`). Your Proxmox host SSH key is injected
  into all clones by `create-vms.sh`.
- **The app/ls VMs are NOT on the LAN** — reach them via the proxy:
  `ssh flowform@10.10.10.20` from inside 210.
- **From the host directly:** `qm guest exec <vmid> -- <cmd>` (qemu-guest-agent is
  baked in), or `qm terminal <vmid>` for a serial console.

## Prerequisites / gotchas

- **Host virtualization must be enabled.** If `qm start` fails with *"KVM
  virtualisation configured, but not available"*, enable **SVM** (AMD) / **VT-x**
  (Intel) in the host BIOS and reboot — `dmesg | grep -i 'disabled by BIOS'`
  confirms. `/dev/kvm` must exist.
- `setup-host.sh` must run first — `create-vms.sh` fails closed if `vmbr10` is
  missing; `create-template.sh` needs `snippets` content on `local` (for cloud-init
  user-data in Phase 3).
- Template disk lives on `ZFS-RAIDZ`; clones are full clones on the same pool.

## Files

| Script | Does | Reversible |
|---|---|---|
| `setup-host.sh` | create `vmbr10`, enable `snippets` on `local` | `--undo` |
| `create-template.sh` | bake golden template 9000 offline (host deps) | `--force` rebuilds |
| `create-localstack-template.sh` | bake ls-vm template 9001 (localstack pre-pulled) | `--force` rebuilds |
| `create-vms.sh` | clone + configure + start 210/220/230 | `--force` reclones |
| `destroy-vms.sh` | stop + destroy 210/220/230 (template kept) | n/a |
```
