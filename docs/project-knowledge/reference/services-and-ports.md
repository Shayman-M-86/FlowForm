---
title: Services and ports
aliases: ["Services and ports"]
document_type: reference
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-27
tags: [infrastructure]
related_code: ["../../../infra/containers/", "../../../infra/deployment/proxmox/cloud-init/", "../../../frontend/docker-compose.dev.yml"]
related_docs: ["Runtime containers", "Local infrastructure"]
---

# Services and ports

This reference records ports explicitly published or bound by maintained
Compose and rehearsal definitions. A binding does not establish live firewall,
security-group, DNS, or external reachability.

| Context | Service | Bind/listener retained from legacy reference |
| --- | --- | --- |
| Development | Core/response PostgreSQL | `127.0.0.1:5432` and `127.0.0.1:5433` |
| Development | Backend | `0.0.0.0:5000` to container `5000` |
| Frontend development | Public site / Studio | `${PUBLIC_SITE_PORT:-4322}` to `4321`; Studio `0.0.0.0:5174` |
| Test | Core/response PostgreSQL and backend | loopback `5442`, `5443`, and `5010` respectively |
| Runtime proxy | Caddy / Squid / Alloy | public `80` and `443`; private proxy/collector ports `3128`, `3500`, `4317` |
| Runtime app | Backend / Alloy | private backend `5000`; Alloy receiver is Compose-network scoped |
| Rehearsal | DB, TLS shim, LocalStack, registry | legacy definitions use private bridge/fixture bindings including `5432`, `443`, `4566`, and `5000` |

Compose definitions under `infra/containers/` and `frontend/docker-compose.dev.yml`
own mappings. Cloud-init and deployment configuration own addresses and firewall
rules. Rescan `ports`, `expose`, listener, and host-network settings before
using this page for operational access.

## Related documents

- [[runtime-containers|Runtime containers]]
- [[local-infrastructure|Local infrastructure]]
