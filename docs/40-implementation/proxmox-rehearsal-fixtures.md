---
title: Proxmox rehearsal fixtures and egress
aliases:
  - "Proxmox rehearsal fixtures and egress"
document_type: implementation
status: draft
authority: canonical
verified_against_commit: null
tags: [infrastructure]
related_code:
  - "../../infra/containers/strategies/rehearsal/"
  - "../../infra/deployment/proxmox/terraform/"
  - "../../infra/deployment/proxmox/scripts/"
  - "../../infra/deployment/bootstrap/"
  - "../../infra/deployment/config/runtime-parameter-contract.json"
related_docs:
  - "Proxmox rehearsal implementation"
  - "Proxmox rehearsal observability"
  - "Proxmox rehearsal setup"
---

# Proxmox rehearsal fixtures and egress

How the offline rehearsal fixtures fake AWS, how every call takes the same
egress shape as real AWS, and the two deliberate holes in that isolation (Auth0
and operator-facing TLS). It describes the checked-in design; it does not claim a
fixture has been built or the rehearsal is end-to-end healthy. For the VM
topology and ownership boundary, see [[proxmox-rehearsal|Proxmox rehearsal implementation]].

## Offline fixture boundary

The proxy retains LAN egress and uses the golden template. LocalStack and the
database have no default route, so their fixtures preload the images named by the maintained
LocalStack, registry, and TLS-shim Compose files before deployment. Terraform
uses template `9001` only for VM `230` and template `9002`, containing only
`postgres:17`, for VM `240`; proxy and app remain on the shared golden template.

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
`infra/deployment/proxmox/scripts/rehearsal verify` asserts all of this against the
live stack (Squid-log CONNECTs present, direct paths blocked, `--disruptive`
proves egress fails when Squid is down).

Terraform validates its non-secret seed map against the shared parameter
contract and renders both into the LocalStack cloud-init payload. A systemd
oneshot waits for LocalStack health and publishes non-secret runtime parameters.
Managed Secrets Manager values arrive later through `rehearsal sync`: the
workstation streams an allow-listed archive assembled from the root-only PVE
bundle and deploy-time Auth0/Grafana inputs into VM 230, where the on-VM helper
validates and reconciles it. Terraform configuration and state contain none of
those secret values.
The AWS CDK security stack uses the same contract for its scoped SSM names but
supplies real AWS resource values. App and proxy bootstrap reads retry to avoid
a simultaneous-start race with the seed service.

Seed resources remain runtime data; the fixture contains none of that state.
Static validation proves the build graph and contract resolve, not that
templates `9001` and `9002` exist on a Proxmox host or the deployed services are healthy.

Backend publication remains an orchestrated operator action. The maintained
helper at `infra/containers/strategies/rehearsal/services/registry/build-and-push-backend.sh`
always relays through app VM `220`: `rehearsal build` owns the temporary
`vmbr10` transport, prepares the app daemon proxy, and reuses one per-build SSH
trust file across image operations. The push itself rides Squid — the app daemon tunnels
`CONNECT registry.localstack.test:443` to the TLS shim, which fronts the private
registry — so it exercises the same egress path a real ECR push would. The
registry and LocalStack are never LAN-facing, and there is no insecure-registry
exception anywhere.

The app Compose stack pulls a second image the offline app box cannot reach on
its own: the Grafana Alloy sidecar. The companion helper
`infra/containers/strategies/rehearsal/services/registry/mirror-alloy-image.sh`
mirrors `grafana/alloy` into the fake registry over the identical relay-through-
`220` path. Backend build and Alloy pull run concurrently with database
convergence. Publication stays sequential through the shared relay, and a
stream is skipped only when the registry manifest's config digest equals the
prepared local image ID. Both images must exist before the orchestrator runs the
app bootstrap; cloud-init no longer starts a competing app convergence.

The app VM uses the shared app Compose unchanged. VM `240` runs one tmpfs-backed
PostgreSQL 17 cluster containing both databases. Its bootstrap briefly opens
host egress only to Squid to retrieve the two app-role passwords, generates the
throwaway cluster-init credential locally, closes egress, and then starts the
preloaded image with `pull_policy: never`. The full maintained database init
tree creates schemas, grants, the NOLOGIN owner, and low-privilege SCRAM roles.
There is no cross-VM Compose dependency: readiness can fail until VM `240` is
healthy and recover afterwards.

## Auth0 boundary — the one live dependency

Auth0 is the one dependency the rehearsal does not fake. The backend validates
bearer tokens against the real dev tenant so that tokens issued to the Studio
front end verify end-to-end. The Squid allow-list admits **two** distinct Auth0
hosts alongside the `*.localstack.test` names, because token validation and the
Management API live on different domains:

- the token **issuer** (`auth.flow-form.com.au`) — request-time JWT validation
  fetches OIDC metadata and JWKS through Squid, exactly as production does;
- the **Management API tenant** (`FLOWFORM_AUTH0_MGMT_DOMAIN`, a `*.au.auth0.com`
  host) — the boot-time management-client check dials `https://<tenant>/oauth/token`.

Both are entries in
`infra/containers/strategies/rehearsal/services/squid/allowed-domains.txt`.
The checked-in Management API entry is the canonical dev tenant used by
`infra/env/dev/.backend.env`; the broader regional suffix beside it keeps the
rehearsal valid for another Australian Auth0 tenant without admitting
non-Auth0 internet destinations.
Admitting only the issuer (as an earlier revision did) lets requests validate but
crash-loops the backend at startup on `APPLICATION STARTUP FAILED` the moment
management validation is enabled, because Squid `403`s the un-listed tenant
CONNECT. This is a deliberate hole in the isolation — authenticated flows require
both hosts reachable and up; unauthenticated endpoints remain fully offline.

The Auth0 identifiers are not committed. Terraform declares them as variables
without defaults, and `rehearsal terraform`/`rehearsal build` export them as
`TF_VAR_*` from the gitignored `infra/env/dev/.backend.env`, so rehearsal and
dev cannot drift apart.

The Management API is functional and uses the real management client secret.
`rehearsal sync` resolves it from `AUTH0_MGMT_SECRET_FILE`, the environment, or
AWS Secrets Manager (`flowform/nonprod/app-secrets` → `auth0_mgmt_secret`) and
streams it into the LocalStack `app-secrets` value without putting it in
Terraform or the persistent bundle. The app validates against the real
Management API at startup and fails loudly on a wrong secret, wrong tenant, or
a tenant host the Squid allow-list does not admit.
Set `AUTH0_MGMT_SECRET` in the environment to override the AWS fetch (e.g. no
login available); the wrapper requires the value and fails fast if it is absent.

## Operator-facing TLS — committed trust anchor

The proxy's Caddy serves a pre-generated leaf for the API domain
(`infra/containers/strategies/rehearsal/services/caddy/certs/api.crt`, regenerated by
`generate-api-cert.sh` beside it) signed by the committed rehearsal CA
(`infra/containers/strategies/rehearsal/services/tls-shim/ca/rehearsal-ca.crt`) — the same
throwaway CA the TLS shim uses for the fake-AWS endpoints. It deliberately does
NOT use Caddy's `tls internal`: that CA is minted inside the VM's data volume,
so every proxy rebuild produced a new root and silently invalidated operators'
installed trust. With the committed CA, operators install `rehearsal-ca.crt`
into their OS trust store once and it survives all rebuilds.

## Related documents

- [[proxmox-rehearsal|Proxmox rehearsal implementation]]
- [[proxmox-rehearsal-observability|Proxmox rehearsal observability]]
- [[proxmox-rehearsal-setup|Proxmox rehearsal setup]]
