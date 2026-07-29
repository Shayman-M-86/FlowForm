---
title: Proxmox rehearsal fixtures and egress
aliases: ["Proxmox rehearsal fixtures and egress"]
document_type: implementation
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-29
tags: [infrastructure, security]
related_code:
  - "../../../../infra/containers/strategies/rehearsal/fixtures/"
  - "../../../../infra/containers/strategies/rehearsal/services/squid/"
  - "../../../../infra/containers/strategies/rehearsal/services/localstack/"
  - "../../../../infra/deployment/proxmox/scripts/lib/cmd_verify.sh"
related_docs:
  - "Proxmox rehearsal"
  - "Proxmox rehearsal observability"
  - "Proxmox rehearsal setup"
---

# Proxmox rehearsal fixtures and egress

Owns the local fixture and egress boundary used by the Proxmox rehearsal. It
describes checked-in configuration, not the live state of a fixture.

```text
App VM
  |
  +--> Squid on Proxy VM --> allowed external Auth0 domains
  |
  +--> Squid on Proxy VM --> TLS shim on Fixtures VM
                                  |
                                  +--> LocalStack
                                  +--> private registry

direct App VM egress to these destinations is expected to fail.
```

## Local fixture boundary

VM 230 runs LocalStack, a TLS shim, and the private registry. LocalStack is
bound to loopback on port `4566`; the TLS shim terminates
`*.localstack.test` traffic on the fixture VM and forwards it to LocalStack or
the registry. The app VM reaches these names through Squid on the proxy rather
than by directly addressing the fixture services.

The rehearsal seed script writes non-secret runtime parameters after LocalStack
is healthy. `rehearsal sync` sends the real secret bundle to the fixture VM;
the receiver stages it in a private tmpfs directory before reconciling the
LocalStack Secrets Manager values. Terraform declares non-secret Auth0
identifiers but explicitly excludes the management secret and Grafana token.

The registry and LocalStack are not LAN-facing. The backend and Alloy image
helpers transfer images through the app VM's Docker daemon and use the same
private relay route; the build command publishes them before app convergence.

## Egress controls and live dependency

The proxy's Squid configuration allows only the domains listed in its rehearsal
allow-list. The verification command creates traffic for the fake AWS and
registry names and checks that the corresponding `CONNECT` records appear in
Squid's access log. It also checks direct paths from the app VM fail while the
same names work through Squid.

Auth0 remains an intentional external dependency: the verification command
exercises the issuer domain `auth.flow-form.com.au`, and Terraform accepts a
separate `*.auth0.com` Management API tenant hostname. No tenant identifiers
or secrets are stated here because they are machine-local inputs.

The proxy API certificate and the fixture TLS certificate are signed by the
checked-in rehearsal CA. This is a local trust anchor; operators must trust it
when accessing the rehearsal API.

## Related documents

- [[proxmox-index|Proxmox rehearsal]]
- [[rehearsal-observability|Proxmox rehearsal observability]]
- [[rehearsal-setup|Proxmox rehearsal setup]]
