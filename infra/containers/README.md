# FlowForm container ownership

The container tree separates immutable image builds from runtime
orchestration:

```text
infra/containers/
├── images/                  # independently published container build contexts
└── runtime/
    ├── common/              # platform-neutral runtime helpers
    ├── aws/common/          # shared AWS App and Proxy Compose topology
    ├── development/         # local development and test runtime
    └── proxmox/rehearsal/   # Proxmox rehearsal adapters and fixtures
```

Each first-class directory under `images/` owns one independently published
container image:

| Context | Owns | Runtime selection |
| --- | --- | --- |
| `images/backend/` | Python runtime, backend source, default command, health probe | None |
| `images/caddy/` | Route 53-enabled Caddy binary and production Caddyfile | Environment variables |
| `images/squid/` | Squid, policy template, AWS allow-list, renderer, validation, health probe | Source CIDR variables |
| `images/alloy/` | Alloy binary plus App and Proxy telemetry configurations | `FLOWFORM_ALLOY_ROLE=app|proxy` |

The checked-in immutable source contract is
`infra/contracts/image-sources.json`. Backend builds from the repository root
because it copies `backend/`; the other three images build from their own
directories.

Container images own service behaviour and configuration templates.
`runtime/` owns Compose topology, runtime helpers, and platform/environment
adapters. Role AMIs may install those runtime assets, but do not own their
repository source. CDK and SSM provide environment identity, internal DNS
names, and promoted immutable image digests. Secrets are mounted at runtime
and are never copied into these build contexts.

The normal AWS images embed the production Caddyfile and Squid destination
allow-list. The Proxmox rehearsal remains an environment adapter: its Compose
override mounts the rehearsal certificate Caddyfile and fake-service Squid
allow-list over those defaults. Development and rehearsal do not maintain
separate copies of the deployable Backend image.

## Local validation

Run the structural checks:

```bash
infra/tests/containers/test-container-invariants.sh
```

When Docker is available, build the self-contained service contexts:

```bash
docker build -f infra/containers/images/caddy/Dockerfile infra/containers/images/caddy
docker build -f infra/containers/images/squid/Dockerfile infra/containers/images/squid
docker build -f infra/containers/images/alloy/Dockerfile infra/containers/images/alloy
```

The Backend publisher uses the repository root as its build context:

```bash
docker build -f infra/containers/images/backend/Dockerfile .
```
