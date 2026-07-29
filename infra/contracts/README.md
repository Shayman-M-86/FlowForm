# Infrastructure contracts

This directory is the canonical, platform-neutral interface between FlowForm's
AWS infrastructure, machine images, containers, and deployment tooling.

| Contract | Purpose |
| --- | --- |
| `runtime-hosts.json` | Stable host paths, role services, AMI parameters, release parameters, and runtime groups |
| `instance-context.schema.json` | The small, non-secret context CDK writes before starting a role service |
| `app-release.schema.json` | Immutable application container release manifest |
| `proxy-release.schema.json` | Immutable proxy container release manifest |
| `runtime-parameters.json` | Non-secret runtime parameters and secret-name mappings |
| `image-sources.json` | Pinned container build and mirror sources |

CDK owns instance identity and AWS resources, but it does not create the
mutable app or proxy release parameters. Release tooling validates a complete
manifest against the corresponding schema and promotes it atomically to the
parameter path declared in `runtime-hosts.json`.

The compatibility link at
`infra/deployment/config/runtime-parameter-contract.json` exists only while
the Proxmox rehearsal is migrated to this canonical location.
