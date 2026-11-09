---
title: Staging cutover to the Proxmox hybrid stack
aliases: ["Staging cutover to the Proxmox hybrid stack", "Staging hybrid cutover"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-11-09
tags: [infrastructure, security, configuration]
related_code: []
change_triggers:
  - "../../../infra/deployment/hybrid/"
  - "../../../infra/deployment/dns/"
  - "../../../infra/deployment/aws/cdk/flowform_infra/stacks/hybrid_identity_stack.py"
  - "../../../infra/deployment/aws/cdk/flowform_infra/stacks/hybrid_runtime_stack.py"
related_docs:
  - "Engineering migrations"
  - "AWS staging runtime convergence"
---

# Staging cutover to the Proxmox hybrid stack

Staging runs on the self-hosted Proxmox hybrid stack (proxy, app and database
VMs) behind a Cloudflare Tunnel. This record tracks the transition from the
AWS EC2 and RDS deployment. Current
implementation and live inspection remain authoritative; the runbooks are
`infra/deployment/hybrid/README.md` and `infra/deployment/hybrid/NETWORK.md`.

## Start and target

- **Start:** the staging frontends call `api.staging.flow-form.com.au` on the
  AWS proxy; Route 53 is authoritative for `flow-form.com.au`.
- **Target:** the staging frontends call `api-staging.flow-form.com.au`, a
  proxied Cloudflare Tunnel route to the hybrid proxy's Caddy. Cloudflare is
  authoritative for the zone, and AWS staging compute and RDS are removed.

The hybrid hosts reuse the AWS bootstraps, release manifests, Parameter Store
configuration and Secrets Manager entries. IAM Roles Anywhere certificates
provide workload identity.

## State on 2026-11-09

Done and verified:

- Template `9100` and VMs `310` (proxy), `320` (app) and `330` (DB) exist, with
  Proxmox guest firewalls managed by Terraform.
- `FlowForm-Staging-HybridIdentity` is deployed; the proxy and app hold
  two-year host certificates expiring November 2028.
- Proxy, DB and app roles are converged on release `fc2cfdad`. The tunnel token
  comes from `flowform/nonprod/tunnel-secrets`; cloudflared is mirrored to
  `flowform-staging-cloudflared` and selected by `CLOUDFLARED_IMAGE`.
- Chrony: the proxy syncs from `time.cloudflare.com` and serves only the app.
- The nameservers moved to Cloudflare at 08:55 UTC and the zone was active by
  08:58 UTC. All imported records are DNS-only except the tunnel hostname.
- `FlowForm-Staging-Frontend` now publishes `vite-api-base-url` as
  `https://api-staging.flow-form.com.au`, and the studio deployed from it.
  Public API readiness, CORS and Auth0 sign-in work through the tunnel.
- `FlowForm-Staging-HybridRuntime` adopted the 30 backend and proxy parameters
  used by Proxmox. It publishes the tunnel hostname as `API_DOMAIN`. Both
  hybrid roles converged using that configuration and public readiness passed.
- The legacy `api.staging.flow-form.com.au` record was removed from both DNS
  providers. `dns-sync check` passed.
- The AWS App, Proxy, DatabaseBootstrap, Database and Network stacks were
  deleted. Both EC2 instances were terminated, and RDS was deleted without
  a final snapshot. AWS listed zero remaining snapshots for the instance.
  Five retired role AMIs, their EBS snapshots and the staging AMI pointers
  were removed.
- Staging CDK now synthesizes the shared Security, Registry, Frontend,
  FrontendCert, HybridRuntime and HybridIdentity stacks. A local copy of the
  public staging CA certificate enables the HybridIdentity stack. The live
  staging CDK diff was clean, both hybrid roles redeployed after teardown,
  and the public API and both frontends returned HTTP 200.
- `staging` merges run CI and then the frontend deploy. The `staging` GitHub
  environment allows `main` because `workflow_run` jobs run in the
  default-branch context.
- `flow-form.com.au` auto-renews through Route 53 Domains (registration
  expires 2027-04-24).
- `seed-secrets.sh` writes to the security-scope paths
  (`flowform/<scope>/...`), reads `infra/deployment/aws/cdk/.env.<env>`, and
  passes values through temporary files. Its earlier env-name paths are the
  likely reason `db-secrets` was never seeded.

The hybrid database is new and holds no AWS staging data.

## Remaining work

### Before relying on staging data

- **Database backups:** schedule logical `pg_dump` backups of both databases
  and a Proxmox backup of VM `330`, then rehearse a restore. Snapshot backups
  are crash-consistent because the guests have no QEMU guest agent; see
  "QEMU guest agent" in the hybrid runbook.
- **Telemetry:** confirm that proxy and app logs and traces reach Grafana Cloud
  (Loki and Tempo). The containers report no errors, but the receiving side is
  unverified.
- **DB time sync:** the DB VM has no time source. Serve it from the app's
  chrony (`allow 172.20.50.20`) and add UDP 123 rules to the app and DB guest
  firewalls.

### Cleanup and hardening

- Move the CA key (`infra/deployment/hybrid/.local/identity/staging-ca.key`) to
  offline storage. Renew host certificates before November 2028 with
  `infra/deployment/hybrid/scripts/identity install proxy|app`.
- Replace the DB administration jump with a dedicated forwarding-only key on
  the app, limited to the DB on TCP 22, and a separate DB login key.
- Decide whether the proxy VLAN should reach Docker Hub; tighten the UniFi
  policy if not.
- Optionally disable cloud-init's first-boot package upgrade, which UniFi
  blocks and which slows the first boot.

## Risks and rollback

- CDK still writes public records to Route 53. Mirror any change into
  Cloudflare; `dns-sync check` reports drift and runs after each stack deploy.
- Recover the staging API by restoring the Proxmox services and tunnel route.
  The former EC2 and RDS deployment has been removed.

## Completion criteria

- The public API works through the tunnel and `dns-sync check` passes.
- Backups are scheduled and a restore has been rehearsed.
- Telemetry arrives in Grafana Cloud.
- AWS staging compute and RDS are removed.
- Maintained documentation reflects the resulting architecture, and this record
  is archived.

## Related documents

- [[migrations-index|Engineering migrations]]
- [[aws-staging-runtime-convergence|AWS staging runtime convergence]]
