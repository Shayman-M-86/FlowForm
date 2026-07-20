---
title: Proxmox rehearsal implementation
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
  - "../../infra/deployment/proxmox/rehearsal-logs.sh"
  - "../../infra/deployment/proxmox/verify-rehearsal.sh"
  - "../../infra/deployment/bootstrap/"
  - "../../infra/containers/rehearsal/"
  - "../../infra/tests/deployment/"
related_docs:
  - "Deployment model"
  - "Machine image building"
  - "Packer implementation"
  - "Infrastructure implementation"
---

# Proxmox rehearsal implementation

Maps the local Proxmox rehearsal boundary to its maintained entry points. It
describes the checked-in design; it does not claim that a fixture has been built
or the rehearsal is end-to-end healthy.

## Ownership boundary

| Layer | Owned responsibility | Main location |
| --- | --- | --- |
| Source preparation | Import the pinned official AL2023 KVM image as a minimal Proxmox source template. | `infra/images/scripts/prepare-proxmox-source.sh` |
| Packer | Build the shared golden template, then derive the offline LocalStack fixture. | `infra/images/packer/`, `infra/images/scripts/build-proxmox-image.sh`, `infra/images/scripts/build-proxmox-localstack-fixture.sh` |
| Host bootstrap | Create the private rehearsal bridge and enable Proxmox snippet storage once. | `infra/deployment/proxmox/host/01-setup-host.sh` |
| Terraform | Render/upload cloud-init and clone the golden template into the rehearsal topology. | `infra/deployment/proxmox/terraform/` |
| Runtime configuration contract | Keep AWS CDK and Proxmox rehearsal SSM parameter names aligned while allowing platform-specific values. | `infra/deployment/config/runtime-parameter-contract.json` |

Packer and Terraform are separate processes. Packer produces a reusable
template; Terraform consumes a completed template by VMID. Terraform does not
invoke Packer, so a base-image change requires a Packer build before Terraform
can deploy clones of that new template.

## Current topology

The default golden template is VMID `9000` and the default fixture is `9001`.
The source (`8999`), golden, and fixture templates use the official image's
native 25 GiB virtual disk. Terraform does not resize disks: new full clones
inherit 25 GiB, while older 32 GiB clones remain 32 GiB until replaced.
Terraform declares:

| VMID | Role | Source | Network |
| --- | --- | --- | --- |
| 210 | Proxy | Golden `9000` | Static `192.168.70.63/22` on `vmbr0` (`proxy_lan_ip`); `10.10.10.10/24` on `vmbr10` |
| 220 | App | Golden `9000` | `10.10.10.20/24` on `vmbr10`; no gateway |
| 230 | LocalStack | Fixture `9001` | `10.10.10.30/24` on `vmbr10`; no gateway |

The proxy's LAN address is static on purpose. It is the one address operators,
docs, and hosts files name, and a DHCP lease does not survive VM recreation:
each rebuild changes the NIC MAC and the machine-id-derived DHCP client
identifier, so the stack came back healthy on a new address while everything
pointing at the old one appeared dead. MAC pinning alone does not fix this.
Keep `proxy_lan_ip` excluded from the LAN router's DHCP pool.

Terraform renders cloud-init locally, embeds its configured public SSH keys in
the custom user-data, uploads the snippets to Proxmox storage, and attaches
them to the clone. This matters because Proxmox custom user data replaces its
generated user-data rather than merging the generated SSH-key section.

## Offline fixture boundary

The proxy retains LAN egress and uses the golden template. LocalStack has no
default route, so its fixture preloads the images named by the maintained
LocalStack, registry, and TLS-shim Compose files before deployment. Terraform
uses that fixture only for VM `230`; proxy and app remain on the shared golden
template.

Cloud-init still writes the Compose files, rehearsal TLS material, service
units, SSH keys, and network-specific configuration, then starts the services.
LocalStack remains private to `vmbr10`; Terraform does not require a LAN-facing
LocalStack endpoint or run an AWS provider against it.

Every fake-AWS and fake-ECR call takes the same egress shape as real AWS:
`app → Squid (CONNECT :443, per-service SNI) → TLS shim on VM 230 →` LocalStack
`:4566` or the registry `:5000`. Image pulls and pushes are included — the
registry is fronted by the shim as `registry.localstack.test`, admitted in the
Squid allow-list exactly as production admits `api.ecr`/`dkr.ecr`, so the app
daemon proxies pulls through Squid rather than trusting a plain-HTTP registry
(there is no `insecure-registries` entry, and the shared daemon `NO_PROXY`
carries no private-CIDR exemption). That bypass path is not merely unused but
closed: LocalStack `:4566` and the registry `:5000` bind to loopback on VM 230,
and an `nftables` ruleset there admits `:443` only from the proxy VM — so a
direct `app → :4566`/`:443` call fails the way an AWS security group would.
`infra/deployment/proxmox/verify-rehearsal.sh` asserts all of this against the
live stack (Squid-log CONNECTs present, direct paths blocked, `--disruptive`
proves egress fails when Squid is down).

Terraform validates its non-secret seed map against the shared parameter
contract and renders both into the LocalStack cloud-init payload. A systemd
oneshot waits for LocalStack health on every boot, generates throwaway secrets
inside the VM, creates local KMS and Secrets Manager resources, and publishes
the resulting local identifiers plus the rehearsal backend/proxy parameters.
The AWS CDK security stack uses the same contract for its scoped SSM names but
supplies real AWS resource values. App and proxy bootstrap reads retry to avoid
a simultaneous-start race with the seed service.

Seed resources remain runtime data; the fixture contains none of that state.
Static validation proves the build graph and contract resolve, not that
template `9001` exists on a Proxmox host or the deployed services are healthy.

The backend image push remains an operator action. The maintained helper at
`infra/containers/rehearsal/services/registry/build-and-push-backend.sh` always
relays through app VM `220`: it temporarily addresses the Proxmox host on
`vmbr10`, creates a proxied SSH path to `220`, streams the built image into that
VM's Docker daemon, and pushes from there before removing the temporary
transport on exit. The push itself rides Squid — the app daemon tunnels
`CONNECT registry.localstack.test:443` to the TLS shim, which fronts the private
registry — so it exercises the same egress path a real ECR push would. The
registry and LocalStack are never LAN-facing, and there is no insecure-registry
exception anywhere.

That helper also mirrors the private-registry dependencies named by the
rehearsal app Compose override, deriving upstream names and tags from Compose.
The app cloud-init layers that override over the production Compose file, so
the two ephemeral PostgreSQL services start only in the rehearsal.

Rehearsal bootstrap force-recreates its throwaway app stack when secrets are
reseeded. Until the repository contains deployable migrations, the override
runs a rehearsal-only one-shot that creates the current SQLAlchemy schema before
the backend starts. This is not evidence for the production migration path.

## Auth0 boundary — the one live dependency

Auth0 is the one dependency the rehearsal does not fake. The backend validates
bearer tokens against the real dev tenant so that tokens issued to the Studio
front end verify end-to-end: the Squid allow-list admits the issuer domain
(`auth.flow-form.com.au`) alongside the `*.localstack.test` names, and the app
box fetches OIDC metadata and JWKS through Squid exactly as production does.
This is a deliberate hole in the isolation — authenticated flows require the
tenant reachable and up; unauthenticated endpoints remain fully offline.

The Auth0 identifiers are not committed. Terraform declares them as variables
without defaults, and the wrapper
`infra/deployment/proxmox/terraform/with-dev-auth0-env.sh` exports them as
`TF_VAR_*` from the gitignored `infra/env/dev/.backend.env`, so rehearsal and
dev cannot drift apart. Run every plan/apply through that wrapper.

The Management API remains intentionally non-functional: it needs the real
management client secret, and the rehearsal seeds random bytes instead. The
seed therefore sets `FLOWFORM_AUTH0_MGMT_VALIDATE_ON_STARTUP=false` so the app
boots; the application default remains `true`, bearer-token validation is
unaffected, and Management API operations still fail closed.

## Operator-facing TLS — committed trust anchor

The proxy's Caddy serves a pre-generated leaf for the API domain
(`infra/containers/rehearsal/services/caddy/certs/api.crt`, regenerated by
`generate-api-cert.sh` beside it) signed by the committed rehearsal CA
(`infra/containers/rehearsal/services/tls-shim/ca/rehearsal-ca.crt`) — the same
throwaway CA the TLS shim uses for the fake-AWS endpoints. It deliberately does
NOT use Caddy's `tls internal`: that CA is minted inside the VM's data volume,
so every proxy rebuild produced a new root and silently invalidated operators'
installed trust. With the committed CA, operators install `rehearsal-ca.crt`
into their OS trust store once and it survives all rebuilds.

## Observability

`infra/deployment/proxmox/rehearsal-logs.sh [app|proxy|registry]` tails
container logs from the private VMs. It temporarily addresses the Proxmox host
on `vmbr10`, jumps through it, restores the isolation invariant on exit
(including interrupt), and flattens the backend's JSON records to one line per
event (`--raw` for full tracebacks, `-e` errors only, `-r` by request id).

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
infra/deployment/proxmox/host/01-setup-host.sh
```

Creates the isolated `vmbr10` bridge and enables snippet storage.

**3. Build the templates (Packer, from the workstation):**

```bash
infra/images/scripts/prepare-proxmox-source.sh            # source template 8999
infra/images/scripts/build-proxmox-image.sh               # golden template 9000
infra/images/scripts/build-proxmox-localstack-fixture.sh  # offline fixture 9001
infra/images/scripts/verify-proxmox-disk-sizes.sh
```

**4. Deploy the topology (Terraform):**

```bash
infra/deployment/proxmox/terraform/render-cloud-init.sh
cd infra/deployment/proxmox/terraform
terraform init
./with-dev-auth0-env.sh apply
```

The wrapper exports the Auth0 `TF_VAR_*`s; plain `terraform apply` will prompt
for them. The apply clones templates into VMs 210/220/230; the LocalStack VM
seeds parameters and secrets on first boot. The app VM's first bootstrap is
EXPECTED to fail at image pull — the registry starts empty (next step).

**5. Push the backend image, then re-run the app bootstrap:**

```bash
infra/containers/rehearsal/services/registry/build-and-push-backend.sh
```

Then re-run the failed one-shot on the app VM (through the temporary `vmbr10`
jump the push script also uses, or after any reboot of VM 220):

```bash
sudo /opt/flowform/scripts/run-bootstrap-app.sh
```

The push relays through app VM 220's Docker daemon, so it requires step 4's
VMs to be running — the ordering apply → push → re-bootstrap is inherent.

**6. Operator workstation trust (once per machine).** Add the hosts entry
`192.168.70.63 api.localstack.test` (Windows: `C:\Windows\System32\drivers\etc\hosts`;
also WSL's `/etc/hosts` if testing from there), then install
`infra/containers/rehearsal/services/tls-shim/ca/rehearsal-ca.crt` into the
trust store — Windows: import into *Trusted Root Certification Authorities*;
Firefox keeps its own store; Node tooling needs
`NODE_EXTRA_CA_CERTS=<path to rehearsal-ca.crt>`. Because the CA is a repo
file, this never has to be repeated after rebuilds.

**7. Verify:**

```bash
curl --cacert infra/containers/rehearsal/services/tls-shim/ca/rehearsal-ca.crt \
  https://api.localstack.test/api/v1/system/health/ready   # 200, verified TLS
infra/deployment/proxmox/rehearsal-logs.sh app --list      # containers healthy
infra/deployment/proxmox/verify-rehearsal.sh               # full egress model
```

`verify-rehearsal.sh` is the definitive check: health `200`, a structurally
valid but unsigned JWT returning `401` (kid mismatch — the live Auth0 JWKS path,
never a `500`), every fake-AWS/ECR name appearing as a `CONNECT` in Squid's
access log, and the direct-bypass paths all blocked. `--disruptive` also stops
Squid to prove egress fails closed. Note it reads Squid's log as the in-container
squid uid (`docker exec -u 13`), which the hardened container requires.

**Teardown and rebuild.** `terraform destroy` removes the VMs and with them the
registry contents and all seeded state. After any full rebuild, repeat steps
4–5 (the templates, host bridge, and workstation trust all survive). VM disks
are disposable by design; fixes belong in the scripts and templates, never
hand-applied to a built VM.

## Related documents

- [[Deployment model]]
- [[Machine image building]]
- [[Packer implementation]]
- [[Infrastructure implementation]]
