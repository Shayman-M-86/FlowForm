# FlowForm infrastructure migration workspace

> TODO(migration): Update all paths, contracts, imports, build contexts, and
> runtime wiring before using anything under `infra-new/`.

`infra-new/` is the one-shot structural replacement for the existing `infra/`
tree. It deliberately models only the intended AWS deployment and does not
carry Proxmox or rehearsal compatibility.

This pass establishes ownership boundaries; it does not make the new tree
runnable.

## Layout

```text
infra-new/
├── contracts/           shared interfaces between release units
├── containers/          independently published container build contexts
├── images/machine/      base, app, and proxy AMI sources
├── cdk/                 AWS resource declarations
├── database/            schema, bootstrap, migrations, and local fixtures
├── operations/          CI and operator-side commands
└── tests/infrastructure/
```

Files with existing AWS-oriented implementations were copied and marked with a
`TODO(migration)` header. New responsibilities are represented by empty
placeholder files. See `MIGRATION-MAP.md` for the migration boundary.

## Rules for the next pass

1. Do not wire `infra-new/` into CI or deployments incrementally.
2. Rework paths and contracts inside this tree until it is internally complete.
3. Keep generated output, local credentials, environment secrets, caches, and
   machine state out of this tree.
4. Remove obsolete compatibility branches while rewiring; do not reproduce the
   old Proxmox and rehearsal seams.
5. Switch repository entry points only after the replacement validates as one
   complete unit.
