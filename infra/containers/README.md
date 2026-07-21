# FlowForm container ownership

Container assets are grouped by responsibility rather than by deployment stage.

- `images/` owns Dockerfiles shared by more than one runtime strategy.
- `runtime/` owns the hardened app and proxy Compose contracts shared by AWS
  staging/production and the Proxmox rehearsal. The proxy stack also runs a
  Grafana Alloy agent (`runtime/services/alloy/`) that ships host and container
  logs to Grafana Cloud (Loki); its credentials arrive via the same
  `/flowform/<scope>/proxy/*` SSM path as the rest of the proxy config.
- `strategies/aws/` owns AWS-specific runtime configuration such as Route 53 TLS
  and the production Squid allow-list.
- `strategies/dev/` owns the writable, source-mounted development and test stacks.
- `strategies/rehearsal/` owns Proxmox-only proxy overrides, the dedicated DB
  fixture, TLS material, and fake-service tooling.

The ordered Compose inputs are:

| Context | Compose files |
| --- | --- |
| AWS app | `runtime/compose/app.yml` |
| AWS proxy | `runtime/compose/proxy.yml` |
| Rehearsal app | `runtime/compose/app.yml` |
| Rehearsal proxy | `runtime/compose/proxy.yml`, then `strategies/rehearsal/compose/proxy.override.yml` |
| Rehearsal DB | `strategies/rehearsal/compose/db.yml` |
| Development | `strategies/dev/compose/compose.yml` |
| Tests | `strategies/dev/compose/compose.test.yml` |

Compose resolves relative bind-mount paths in every override against the
directory of the first Compose file. Rehearsal override paths are therefore
written relative to `runtime/compose/`. The app and DB are separate VM stacks;
Compose does not order them. Backend readiness may fail until VM 240 is healthy
and then recover without recreating the app stack.
