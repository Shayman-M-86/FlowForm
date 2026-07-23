# FlowForm container ownership

Container assets are grouped by responsibility rather than by deployment stage.

- `images/` owns deployable base image definitions shared across strategies,
  currently the Backend image.
- `runtime/` owns the hardened app and proxy Compose contracts shared by AWS
  staging/production and the Proxmox rehearsal. The proxy stack also runs a
  Grafana Alloy agent (`runtime/services/alloy/`) that ships host and container
  logs to Grafana Cloud (Loki); its credentials arrive via the same
  `/flowform/<scope>/proxy/*` SSM path as the rest of the proxy config.
- `strategies/aws/` owns AWS-specific runtime configuration and image
  definitions, including the custom Caddy image compiled with the Route 53 DNS
  provider and the immutable source manifest consumed by AWS deployment
  automation. The Proxmox rehearsal deliberately keeps the stock Caddy image
  because its override mounts a pre-generated certificate instead of
  exercising Route 53 DNS-01.
- `strategies/dev/` owns the writable, source-mounted development and test stacks.
- `strategies/rehearsal/` owns Proxmox-only proxy overrides, the dedicated DB
  fixture, TLS material, and fake-service tooling.

The ordered Compose inputs are:

| Context | Compose files |
| --- | --- |
| AWS app | `runtime/compose/app.yml` |
| AWS proxy | `runtime/compose/proxy.yml`, then `strategies/aws/compose/proxy.override.yml` |
| Rehearsal app | `runtime/compose/app.yml` |
| Rehearsal proxy | `runtime/compose/proxy.yml`, then `strategies/rehearsal/compose/proxy.override.yml` |
| Rehearsal DB | `strategies/rehearsal/compose/db.yml` |
| Development | `strategies/dev/compose/compose.yml` |
| Tests | `strategies/dev/compose/compose.test.yml` |

Compose resolves relative bind-mount paths in every override against the
directory of the first Compose file. AWS and rehearsal override paths are
therefore written relative to `runtime/compose/`. The app and DB are separate
VM stacks; Compose does not order them. Backend readiness may fail until VM 240
is healthy and then recover without recreating the app stack.

Deployed Compose has no default image tags. Bootstrap must supply
`BACKEND_IMAGE` and app-host `ALLOY_IMAGE`, or `CADDY_IMAGE`, `SQUID_IMAGE`, and
proxy-host `ALLOY_IMAGE`, as appropriate. The publisher under
`infra/deployment/aws/scripts/` produces candidate digest references; it does
not make a candidate active.
