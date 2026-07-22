---
title: Proxmox rehearsal observability
aliases:
  - "Proxmox rehearsal observability"
document_type: implementation
status: draft
authority: canonical
verified_against_commit: null
tags: [infrastructure]
related_code:
  - "../../infra/deployment/proxmox/scripts/"
  - "../../infra/containers/runtime/services/alloy/"
  - "../../infra/containers/runtime/services/alloy-app/"
  - "../../infra/containers/runtime/services/squid/squid.conf"
  - "../../infra/containers/runtime/compose/"
  - "../../infra/containers/strategies/rehearsal/services/registry/"
related_docs:
  - "Proxmox rehearsal implementation"
  - "Proxmox rehearsal fixtures and egress"
  - "Proxmox rehearsal setup"
---

# Proxmox rehearsal observability

How logs are read from and shipped off the Proxmox rehearsal VMs. It describes
the checked-in design; it does not claim the rehearsal is end-to-end healthy.
For the VM topology this refers to, see the topology table in
[[proxmox-rehearsal|Proxmox rehearsal implementation]].

## Log tailing

`infra/deployment/proxmox/scripts/rehearsal logs [app|proxy|fixtures|db]` tails
container logs from the private VMs. It temporarily addresses the Proxmox host
on `vmbr10`, jumps through it, restores the isolation invariant on exit
(including interrupt), and flattens the backend's JSON records to one line per
event (`--raw` for full tracebacks, `-e` errors only, `-r` by request id).

## Log shipping to Grafana Cloud

Two Grafana Alloy agents ship logs off the VMs to Grafana Cloud (Loki). It is
**logs only** — no metrics, no traces, no application instrumentation. The proxy
box (210) has an egress route and pushes directly; the app box (220) has no
gateway (see the topology table in [[proxmox-rehearsal|Proxmox rehearsal implementation]]), so it
cannot reach Grafana Cloud and its agent relays through the proxy over the
private `10.10.10.0/24` net instead of opening an internet hole in the Squid
allow-list.

- **Proxy agent** (`infra/containers/runtime/services/alloy/config.alloy`, run by
  the `alloy` service in `infra/containers/runtime/compose/proxy.yml`) collects
  the host systemd journal and every proxy-box container (`caddy`, `squid`, and
  `alloy` itself) and writes them to Grafana Cloud via `loki.write`
  (`basic_auth` from the three `GRAFANA_CLOUD_*` env values). It also exposes a
  `loki.source.api` receiver on `:3500` that fans the app box's records out to
  the same sink. Squid preserves one `level=info` file access log for
  `rehearsal verify`; the container entrypoint tails that file to stdout, allowing
  Docker discovery to publish it under `service_name="squid"`. Proxy-box containers log plain text,
  so the pipeline extracts a `level` label by regex but does no JSON parsing.
- **App agent** (`infra/containers/runtime/services/alloy-app/config.alloy`, run
  by the `alloy` service in `infra/containers/runtime/compose/app.yml`) collects
  the backend container and forwards to `http://<PROXY_PRIVATE_IP>:3500` via
  `loki.write "gateway"`. The backend emits one JSON object per record
  (`FLOWFORM_LOGGING_LOG_JSON=true`), so a `loki.process` stage — scoped to
  `{service_name="backend"}` so gunicorn's plain-text banner passes through —
  parses the JSON, replaces the log line with the human `message`, and promotes a
  small set of fields to labels.

Both agents run as `user: root` under `cap_drop: [ALL]` with only
`DAC_OVERRIDE` and `DAC_READ_SEARCH` restored: the root-owned journal and Docker
socket and the `alloy`-owned `0770` storage volume are otherwise unreadable/
unwritable even to root once all capabilities are dropped. The docker socket and
journal are mounted read-only; state (WAL, positions) lives in the writable
`alloy_data` named volume, which is why the container is not `read_only`. The app
box's default image is `grafana/alloy` from Docker Hub, but the offline box
cannot reach it, so its bootstrap env overrides `ALLOY_IMAGE` to the
fake-registry mirror (`registry.localstack.test/grafana/alloy:…`, pushed by
`infra/containers/strategies/rehearsal/services/registry/mirror-alloy-image.sh`
the same relay way as the backend image).

**Label discipline.** Loki indexes by label and every distinct label-value
combination is a stream, so only low-cardinality fields become labels
(`service_name`, `service`, `container`, `level`, `method`, `event_type`, and the
static `environment`/`platform`/`host_role`). Per-request context —
`request_id`, the raw `path` (carries UUIDs), `status_code`, `duration_ms` —
stays as parsed fields. `service_name` is derived from the
`com.docker.compose.service` label on each container because Grafana Logs
Drilldown keys on it; without it logs surface as "Unknown". The
`environment`/`platform`/`host_role` labels are static constants in each config
because each file ships to exactly one box; they must become env-driven if Alloy
later runs on real AWS.

**Credential seam.** The non-secret Grafana URL and user follow the same
prod-shaped SSM path as `CADDY_IMAGE` and `API_DOMAIN`. The token is resolved by
`rehearsal sync` from `GRAFANA_CLOUD_TOKEN_FILE`, the environment, or the
gitignored `infra/env/dev/.grafana.env`, then reconciled into the LocalStack
observability secret. `bootstrap-proxy.sh` materialises that secret under the
host tmpfs while rendering non-secret proxy parameters into `proxy.env` for
Compose. Terraform configuration and state contain no token value.

## Related documents

- [[proxmox-rehearsal|Proxmox rehearsal implementation]]
- [[proxmox-rehearsal-fixtures|Proxmox rehearsal fixtures and egress]]
- [[proxmox-rehearsal-setup|Proxmox rehearsal setup]]
