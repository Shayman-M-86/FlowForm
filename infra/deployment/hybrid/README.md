# FlowForm hybrid deployment

Deploy three Proxmox VMs for the API gateway, backend and PostgreSQL. The AWS
frontends, release registry, KMS, Secrets Manager, Parameter Store and SES use
their existing deployment paths. The same hybrid adapter can target staging
with the `nonprod` AWS scope or production with the `prod` scope. Use a separate
Proxmox target or checkout and state for each installation. The reserved VM IDs
below allow one installation per cluster.

## Prerequisites

- Apply the [network guide](NETWORK.md) as a separate operator change. Reserve
  template ID `9100` and guest IDs `310` (proxy), `320` (app) and `330` (DB).
- Prepare the maintained Amazon Linux 2023 Proxmox source template and a
  temporary, restricted build network. Reuse the [machine-image tooling](../../machine-images/tooling/README.md)
  and its source preparation procedure if the source template is missing.
- Use a deployment workstation with Packer, Terraform, SSH, jq and Docker.
  Set the Proxmox Terraform API token through `PROXMOX_VE_API_TOKEN`. Both tools
  must trust the Proxmox API certificate. If you use a private CA, source your
  ignored `infra/deployment/hybrid/.local/terraform.env` to export the token
  and `SSL_CERT_FILE` before running Terraform.
- Have the existing AWS scope configuration, frontend and ECR repositories
  available. Promote the app and proxy digest manifests to
  `/flowform/<environment>/app/release` and `/flowform/<environment>/proxy/release`
  through the [AWS container release operations](../aws/operations/README.md).
  Use the same scope for application config, encryption resources and secrets.
  In the existing `/flowform/<scope>/proxy/` Parameter Store group, set
  `CLOUDFLARED_IMAGE` to a full image digest for cloudflared 2025.4.0 or later.
  An approved ECR mirror can supply this image.
- Seed the scope's secrets the same way as for AWS. Deploy the security stack,
  then run `infra/deployment/aws/scripts/seed-secrets.sh` for `app-secrets` and
  `db-secrets`, `seed-observability-secret.sh` for the Grafana token, and
  `seed-tunnel-secret.sh --environment <env> --apply` with
  `CLOUDFLARE_TUNNEL_TOKEN_FILE` for the remotely managed Cloudflare Tunnel
  token. Hybrid hosts read the same entries as AWS.
- Publish a Squid image built from the current
  [allow-list](../../containers/images/squid/allowed-domains.txt). It includes
  the Roles Anywhere and ECR layer-bucket hosts that hybrid app hosts need.

## Build and provision

Prepare the Proxmox node after the UniFi trunk and zone policies are in place.
The two host scripts in `scripts/` are independent. Run each as root on the node, or stream it
over the existing Proxmox SSH connection.

| Script | Owns |
| --- | --- |
| [`setup-host.sh`](scripts/setup-host.sh) | VLAN-aware `vmbr1`, private `vmbr2`, and host IPv6 settings for those bridges and `nic0` |
| [`setup-firewall.sh`](scripts/setup-firewall.sh) | Standalone Proxmox node and Datacenter firewall activation |
| [`terraform/firewall.tf`](terraform/firewall.tf) | Guest SSH security group, VM firewall policies, and per-NIC source address filters |
| [`converge`](scripts/converge) | Guest service startup, including installation of the app's forwarding guard |

Both host scripts default to `--check`. For the first host firewall activation,
keep local console access available and run `setup-firewall.sh --apply
192.168.68.106` using the authorized workstation. The script enables Proxmox
filtering with a default-drop host input policy and a five-minute rollback. It
allows TCP `22` and `8006` from that workstation on `vmbr0`, including access
for Packer and Terraform, and overrides Proxmox's broader built-in management
exceptions. It refuses to replace an existing policy. The GUI's browser console
uses the web UI connection. A separate SPICE client requires its own rule.

Verify fresh SSH and web UI connections from the authorized workstation, and
test denial from another LAN device. From the authorized workstation, run
`setup-firewall.sh --confirm 192.168.68.106` within five minutes to keep the
policy. Wait for rollback if a check fails. Avoid rebooting or editing firewall
rules during this verification window.

Use the existing Proxmox Packer variables as the starting point for a protected,
dedicated hybrid `.pkrvars.hcl` file. Select the temporary build bridge and
address in that file. The hybrid target fixes the output at
`flowform-hybrid-al2023` / `9100` and records a separate build manifest.

```sh
export FLOWFORM_HYBRID_PACKER_VARS=/absolute/path/hybrid.pkrvars.hcl
infra/deployment/hybrid/scripts/hybrid image --validate-only
infra/deployment/hybrid/scripts/hybrid image
```

Put cluster, storage, SSH keys and network values in
`infra/deployment/hybrid/terraform/terraform.tfvars`. The example in this
directory uses the proposed addresses from the network guide. Review the plan
before applying. Set `vm_sizes` for the expected database growth and verify the
guest root filesystem has expanded after cloning. Keep the state private and
backed up.

Set `admin_ipv4` to the deployment workstation's source address. In UniFi, add
the two scoped TCP `22` rules from this workstation to the ingress and app IPs.
Confirm the guest time source and any required NTP policy before convergence.

```sh
infra/deployment/hybrid/scripts/hybrid vm init
infra/deployment/hybrid/scripts/hybrid vm plan
infra/deployment/hybrid/scripts/hybrid vm apply
```

The first apply creates the VMs powered off so Terraform can install their
firewall policies before they have network access. Verify filtering is enabled
on the Proxmox host and the three VM policies are enabled, then start the guests
in Proxmox. Set **Start at boot** there if wanted. Later Terraform applies
preserve the operator's power and boot settings.

Configure trusted SSH aliases `flowform-hybrid-proxy`, `flowform-hybrid-app`
and `flowform-hybrid-db` for the admin deployment path. Use the `ec2-user`
cloud-init account with noninteractive sudo and authenticate each host key
through a trusted path. The deploy wrapper checks both the hostname and its
Terraform address before sending any artifacts. Use the restricted DB admin
path described in the network guide.

### QEMU guest agent

The hybrid guests run without the QEMU guest agent. Amazon Linux 2023 does not
package `qemu-guest-agent` (its repositories ship only `qemu-img`), so the
template cannot install it with `dnf`. Proxmox shuts guests down through ACPI,
and the UI does not report guest addresses.

Snapshot-mode backups of the DB VM are crash-consistent rather than
filesystem-frozen. PostgreSQL recovers from a crash-consistent copy of its
single data disk through WAL replay. Take scheduled logical backups as well
before production use.

To add the agent later, supply a maintained build first, for example compiling
`qemu-ga` from a pinned and checksummed QEMU release during the image build.
Then change these places together:

- [`configure-proxmox-guest.sh`](../../machine-images/packer/provisioners/proxmox/configure-proxmox-guest.sh):
  install the agent and run `systemctl enable qemu-guest-agent`. This
  provisioner runs only for Proxmox builds, so AWS AMIs are unaffected.
- [`proxmox.pkr.hcl`](../../machine-images/packer/sources/proxmox.pkr.hcl):
  `qemu_agent = false` can stay, because the build uses a static address and
  Terraform sets the clones' agent option.
- [`terraform/main.tf`](terraform/main.tf): add `agent { enabled = true }`
  (optionally `trim = true`) to `proxmox_virtual_environment_vm.role`, where
  the comment marks the omission.
- Rebuild template `9100`, then recreate or update the guests. The VMs have
  `prevent_destroy` and the DB VM has Proxmox protection. Stop the guests,
  update the option and confirm the agent responds with `qm agent <id> ping`.
  If guests are instead destroyed in Proxmox and recreated, also remove
  `proxmox_virtual_environment_firewall_rules.guest` and
  `proxmox_virtual_environment_firewall_options.guest` from Terraform state.
  Destroying a VM deletes its firewall file, but Terraform does not detect that
  and would otherwise leave the new guests without their rules.

## Provision the host inputs

Application and proxy environment files are rendered on the VMs by the
existing bootstraps from `/flowform/<scope>/backend/` and
`/flowform/<scope>/proxy/`. The hybrid adapter supplies the private addresses,
substitutes the local PostgreSQL host and password authentication for RDS
connectivity, and retains the configured database names and app users
(`flowform_core` / `flowform_core_app` and
`flowform_response` / `flowform_response_app`). The existing bootstrap retrieves
the common application secrets and Grafana token into file-backed runtime
mounts. The backend retrieves the linkage secret directly through its normal
AWS client.

The hybrid hosts use the AWS secret flow unchanged. The proxy bootstrap
materialises the Grafana token from `observability-secrets` and the Cloudflare
Tunnel token from `tunnel-secrets` into tmpfs. The app bootstrap materialises
`app-secrets` and `db-secrets` into tmpfs, as the rehearsal password strategy
does. Squid uses the allow-list built into its image.

The DB VM has no route to AWS. `hybrid deploy db` reads `db-secrets` with the
workstation's AWS session and streams the two role passwords to
`/etc/flowform/db` on the DB host (root-owned, mode 0600). On its first
convergence the DB host generates its own PostgreSQL superuser password and a
private CA and server certificate for its bridge address, then discards the CA
key. `hybrid deploy app` copies only the public CA certificate into the app
release for libpq `verify-full`. Changing the password files alone does not
rotate PostgreSQL credentials. The initializer uses the shared schema and role
SQL and runs only on empty data storage, so preserve the DB volume and back it
up.

Workload identity is the only per-host input. IAM Roles Anywhere replaces
the EC2 instance role: each host holds an X.509 certificate from a private CA
and exchanges it for temporary credentials through `aws_signing_helper`.

| Piece | Where |
| --- | --- |
| Private CA | `identity/<env>-ca.crt` (public certificate) and `.local/identity/<env>-ca.key`. Both are gitignored. Keep the key offline between renewals. |
| Trust anchor, roles, profiles | CDK stack `FlowForm-<Env>-HybridIdentity`, synthesized only when the CA certificate exists. The proxy role mirrors the EC2 proxy role without Route 53, plus the tunnel secret and cloudflared repository. The app role mirrors `AppTaskRole`. Each role trusts only this anchor and its host's certificate CN. |
| Host files | `/etc/flowform/aws/{config,cert.pem,key.pem,aws_signing_helper}` on the proxy and app, defining the `flowform-runtime` profile. The app profile adds `--with-proxy`, and the backend uses it through its read-only mount. |

```sh
infra/deployment/hybrid/scripts/identity ca            # once per environment
# deploy FlowForm-<Env>-HybridIdentity with operations/stacks/deploy.sh
infra/deployment/hybrid/scripts/identity install proxy
infra/deployment/hybrid/scripts/identity install app   # after the proxy runs Squid
```

`install` asks the host to generate its own key and CSR, signs a two-year
client certificate after checking the CN, installs the pinned and checksummed
helper with the profile, and then reads the role's release parameter through
that profile. Rerun it to renew before expiry. The app check reaches AWS through
Squid, so deploy the proxy role first.

## Converge and verify

Select an approved digest for the official PostgreSQL 17 image. The workstation
pulls and verifies it, then streams it over SSH if the expected image ID is
missing on the DB guest. The DB guest uses a persistent Compose volume and its
runtime declares `pull_policy: never`.

```sh
export HYBRID_POSTGRES_REF='postgres@sha256:<approved-digest>'
infra/deployment/hybrid/scripts/hybrid deploy all
infra/deployment/hybrid/scripts/hybrid status
```

The wrapper installs and restarts the role services in proxy, DB, app order.
The services converge on reboot. For routine app and proxy releases, promote
the new manifests and run `deploy proxy` and `deploy app` as needed. A deploy
recreates the app or proxy containers to pick up refreshed mounts. The DB role
checks a completion marker as well as server readiness. If first initialization
is interrupted, inspect or restore storage before retrying. Back up both
databases and rehearse restore before production use. Database major upgrades,
existing-data migration and password rotation require a separate maintenance
procedure.

Leave the tunnel's public hostname route disabled until the network checks and
private API readiness pass. Then map the existing `API_DOMAIN` hostname to
`http://caddy:80` in Cloudflare, preserving that Host header. Verify public
HTTPS readiness, browser CORS and Auth0 sign-in, a real encrypted survey flow,
SES delivery and Alloy telemetry. If the public API hostname changes, update
the existing frontend configuration and publish through the normal frontend
workflow. Inventory and retire AWS compute or RDS separately after cutover.

KMS is used to wrap new survey keys and unwrap existing ones on a cache miss.
Process-local cached keys can serve some requests through a short outage.
Cold starts, uncached work and new key creation still depend on AWS availability.
