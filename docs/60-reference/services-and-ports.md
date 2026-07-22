---
title: Services and ports
aliases:
  - "Services and ports"
document_type: reference
status: draft
authority: canonical
verified_against_commit: ad26b87e9820
tags: [infrastructure]
related_code:
  - "../../infra/containers/"
  - "../../infra/deployment/proxmox/cloud-init/"
  - "../../frontend/docker-compose.dev.yml"
related_docs:
  - "Runtime containers"
  - "Local infrastructure"
---

# Services and ports
Provides concise verified reference facts for services and ports.

## Reference scope

This page records ports explicitly published or bound by maintained Compose and rehearsal definitions. A listed port is not proof that a live firewall, security group, or host currently exposes it.

## Canonical source

Compose files under `infra/containers/` and `frontend/docker-compose.dev.yml` own container mappings. Cloud-init and deployment configuration own host addresses and firewall rules; application defaults alone do not establish external reachability.

## Entries

| Context | Service | Host bind | Container/listener | Exposure intent |
| --- | --- | --- | --- | --- |
| Development | Core PostgreSQL | `127.0.0.1:5432` | configured core DB port, normally `5432` | Host loopback only. |
| Development | Response PostgreSQL | `127.0.0.1:5433` | configured response DB port, normally `5432` | Host loopback only. |
| Development | Backend | `0.0.0.0:5000` | `5000` | Published by the current dev Compose definition. |
| Frontend development | Public site | `${PUBLIC_SITE_PORT:-4322}` | `4321` | Development Compose host mapping. Direct `astro dev` uses its own default/configuration. |
| Frontend development | Studio | `0.0.0.0:5174` | `5174` | Vite development server. |
| Frontend preview | Studio preview | `0.0.0.0:4173` | `4173` | Enabled by the `preview` profile. |
| Test | Core PostgreSQL | `127.0.0.1:5442` | configured core DB port | Offset so dev and test stacks can coexist. |
| Test | Response PostgreSQL | `127.0.0.1:5443` | configured response DB port | Offset so dev and test stacks can coexist. |
| Test | Backend | `127.0.0.1:5010` | `5000` | Test stack only. |
| Runtime proxy | Caddy | `0.0.0.0:80`, `0.0.0.0:443` | `80`, `443` | Public HTTP/HTTPS entry point. |
| Runtime proxy | Squid | `${PROXY_PRIVATE_IP}:3128` | `3128` | Private app egress proxy. |
| Runtime proxy | Alloy gateway | `${PROXY_PRIVATE_IP}:3500` | `3500` | Private log receiver for the app host. |
| Runtime app | Backend | `${APP_PRIVATE_IP}:5000` | `5000` | Private bind intended for proxy access. |
| Rehearsal DB | PostgreSQL | `10.10.10.40:5432` | `5432` | Rehearsal private bridge. |
| Rehearsal fixture | TLS shim | `10.10.10.30:443` | host-network `443` | HTTPS/SNI front door for LocalStack and the fixture registry. |
| Rehearsal fixture | LocalStack | `127.0.0.1:4566` | `4566` | Fixture-host loopback; TLS shim/proxy provides the remote path. |
| Rehearsal fixture | Registry | `127.0.0.1:5000` | `5000` | Fixture-host loopback behind the TLS shim. |

## Update procedure

Rescan `ports`, `expose`, listener, and host-network settings. Record the explicit bind address and environment interpolation separately, and review firewall/security-group definitions before describing a port as reachable.

## Related documents

- [[runtime-containers|Runtime containers]]
- [[local-infrastructure|Local infrastructure]]
