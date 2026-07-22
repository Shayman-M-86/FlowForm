---
title: Proxmox rehearsal fixtures and egress
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
topology and ownership boundary, see [[Proxmox rehearsal implementation]].

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
`infra/deployment/proxmox/scripts/verify.sh` asserts all of this against the
live stack (Squid-log CONNECTs present, direct paths blocked, `--disruptive`
proves egress fails when Squid is down).

Terraform validates its non-secret seed map against the shared parameter
contract and renders both into the LocalStack cloud-init payload. A systemd
oneshot waits for LocalStack health on every boot, generates throwaway secrets
inside the VM (except the real Auth0 management client secret, which Terraform
supplies — see the Auth0 boundary below), creates local KMS and Secrets Manager
resources, and publishes the resulting local identifiers plus the rehearsal
backend/proxy parameters.
The AWS CDK security stack uses the same contract for its scoped SSM names but
supplies real AWS resource values. App and proxy bootstrap reads retry to avoid
a simultaneous-start race with the seed service.

Seed resources remain runtime data; the fixture contains none of that state.
Static validation proves the build graph and contract resolve, not that
templates `9001` and `9002` exist on a Proxmox host or the deployed services are healthy.

The backend image push remains an operator action. The maintained helper at
`infra/containers/strategies/rehearsal/services/registry/build-and-push-backend.sh` always
relays through app VM `220`: it temporarily addresses the Proxmox host on
`vmbr10`, creates a proxied SSH path to `220`, streams the built image into that
VM's Docker daemon, and pushes from there before removing the temporary
transport on exit. The push itself rides Squid — the app daemon tunnels
`CONNECT registry.localstack.test:443` to the TLS shim, which fronts the private
registry — so it exercises the same egress path a real ECR push would. The
registry and LocalStack are never LAN-facing, and there is no insecure-registry
exception anywhere.

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
front end verify end-to-end: the Squid allow-list admits the issuer domain
(`auth.flow-form.com.au`) alongside the `*.localstack.test` names, and the app
box fetches OIDC metadata and JWKS through Squid exactly as production does.
This is a deliberate hole in the isolation — authenticated flows require the
tenant reachable and up; unauthenticated endpoints remain fully offline.

The Auth0 identifiers are not committed. Terraform declares them as variables
without defaults, and the wrapper
`infra/deployment/proxmox/scripts/with-dev-auth0-env.sh` exports them as
`TF_VAR_*` from the gitignored `infra/env/dev/.backend.env`, so rehearsal and
dev cannot drift apart. Run every plan/apply through that wrapper.

The Management API is functional and uses the real management client secret. The
same wrapper fetches it from AWS Secrets Manager
(`flowform/nonprod/app-secrets` → `auth0_mgmt_secret`, the source the dev stack's
`fetch-dev-secrets.sh` also reads) using the operator's `aws login`, and exports
it as `TF_VAR_auth0_mgmt_secret` (declared as a `secret_seed_value_key` in the
runtime-parameter contract). Terraform merges it into the LocalStack seed
environment, and `seed-localstack.sh` writes it into the `app-secrets`
Secrets Manager entry in place of the throwaway it generates for
`app_secret_key`. Because the secret is real, the seed sets
`FLOWFORM_AUTH0_MGMT_VALIDATE_ON_STARTUP=true`: the app validates against the
real Management API at startup and fails loudly on a wrong secret or tenant.
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

- [[Proxmox rehearsal implementation]]
- [[Proxmox rehearsal observability]]
- [[Proxmox rehearsal setup]]
