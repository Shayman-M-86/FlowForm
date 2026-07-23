---
title: Image script consolidation plan
aliases:
  - "Image script consolidation plan"
document_type: planning
status: draft
authority: planning
verified_against_commit: null
tags: [infrastructure, tooling]
related_code:
  - "../../../infra/images/"
  - "../../../infra/tests/images/"
change_triggers:
  - "../../../infra/deployment/proxmox/"
  - "../../../.github/workflows/"
related_docs:
  - "Active plans"
  - "Machine image building"
  - "Packer implementation"
  - "Scripts implementation"
---

# Image script consolidation plan

## Completion

Implemented in the working tree on 2026-07-23. The public surface is the single
`infra/images/scripts/image` dispatcher, legacy public executables were removed,
the ignored Proxmox source configuration moved to `infra/images/config/`, and
the full structural/Packer validation suite passed. AWS publication was tightened
to accept a CDK environment instead of an arbitrary SSM parameter, so the
destination and region come from `flowform_infra/config/environments.py`.

## Purpose

Replace the nine public shell scripts under `infra/images/scripts/` with one
operator entry point and a small set of sourced implementation libraries. The
result should resemble the Proxmox `rehearsal` dispatcher: discoverable
subcommands, shared preflight/configuration/logging, safe aggregate workflows,
and one root operator README.

This document records the implemented migration plan. Current operator behavior
is documented in `infra/images/README.md` and
[[machine-image-building|Machine image building]].

## Verified current surface

The plan was prepared against commit `cf1429acd92e` plus the current working
tree. Current operator behavior is split across:

- four build wrappers for AWS golden, Proxmox golden, LocalStack fixture, and
  PostgreSQL fixture images;
- separate Proxmox source preparation and disk verification scripts;
- separate AWS manifest extraction, AMI verification, and SSM publication
  scripts; and
- `scripts/lib/packer-build.sh`, which already owns temporary flat Packer
  project assembly.

The split duplicates logging, prerequisite checks, path discovery, Proxmox
environment loading, AWS artifact parsing, and recovery messages. It also
forces documentation to teach filenames and sequencing instead of one command
surface.

## Target operator contract

Create one executable public entry point:

```text
infra/images/scripts/image
```

The recommended grammar is operation-first, matching `rehearsal build` and
keeping commands readable from the repository root:

```bash
# Inspect local tools, configuration, credentials, and remote reachability.
infra/images/scripts/image doctor aws
infra/images/scripts/image doctor proxmox
infra/images/scripts/image doctor all

# Proxmox source template: preflight is read-only by default.
infra/images/scripts/image prepare proxmox
infra/images/scripts/image prepare proxmox --apply
infra/images/scripts/image prepare proxmox --apply --replace

# Selected or complete image lineage builds.
infra/images/scripts/image build aws
infra/images/scripts/image build proxmox golden
infra/images/scripts/image build proxmox localstack
infra/images/scripts/image build proxmox db
infra/images/scripts/image build proxmox all

# Validate definitions/artifacts without rebuilding them.
infra/images/scripts/image verify aws
infra/images/scripts/image verify proxmox
infra/images/scripts/image verify all

# Read or publish the latest AWS artifact.
infra/images/scripts/image artifact aws
infra/images/scripts/image publish aws --environment staging
```

`build proxmox all` must run source preflight, golden, LocalStack fixture, DB
fixture, and final disk verification in dependency order. It must not create or
replace the source template implicitly: a missing or mismatched source reports
the exact `prepare proxmox --apply` command. The two fixtures remain sequential
because they share the reserved Packer build address and Proxmox builder state.

`build aws` retains automatic post-build AMI verification. Individual Proxmox
builds retain post-build disk verification. `--validate-only` and
`--syntax-only` become documented dispatcher options instead of hidden
environment-variable-only interfaces.

## Legacy-to-target mapping

| Current executable | Target command |
| --- | --- |
| `prepare-proxmox-source.sh` | `image prepare proxmox` |
| `build-proxmox-image.sh` | `image build proxmox golden` |
| `build-proxmox-localstack-fixture.sh` | `image build proxmox localstack` |
| `build-proxmox-db-fixture.sh` | `image build proxmox db` |
| `verify-proxmox-disk-sizes.sh` | `image verify proxmox` |
| `build-aws-image.sh` | `image build aws` |
| `verify-aws-ami.sh` | `image verify aws` |
| `extract-aws-ami-id.sh` | `image artifact aws` |
| `publish-aws-ami.sh` | `image publish aws --environment <dev\|staging\|prod>` |

After callers, tests, and documentation migrate, delete the legacy executables.
Do not leave compatibility wrappers: they would recreate multiple supported
entry points and allow behavior to drift.

## Target filesystem

```text
infra/images/
├── README.md                         operator quick start and command reference
├── IMAGE-CONTRACT.md                 image content and lineage contract
├── config/
│   ├── proxmox-source.env.example    committed source-template settings
│   └── proxmox-source.env            ignored local values
├── packer/                           canonical HCL, provisioners, manifests
│   └── assets/
│       └── source-bootstrap.user-data.yaml
└── scripts/
    ├── image                         sole executable operator dispatcher
    ├── image-common.sh               paths, structured logs, summaries, cleanup
    └── lib/
        ├── cmd_artifact.sh
        ├── cmd_build.sh
        ├── cmd_doctor.sh
        ├── cmd_prepare.sh
        ├── cmd_publish.sh
        ├── cmd_verify.sh
        ├── aws-artifact.sh
        ├── aws-session.sh
        ├── packer-project.sh
        ├── proxmox-config.sh
        └── proxmox-remote-source.sh
```

Only `scripts/image` is executable. Command libraries are sourced and expose a
single `cmd_<operation>_main` function. The large embedded remote source script
should move into a dedicated library or asset that is streamed over SSH; this
keeps workstation parsing/configuration separate from PVE-host mutations.

Packer HCL variables stay under `packer/variables/`. Only the shell-consumed
Proxmox source environment moves from the ambiguous `scripts/.env` to
`config/proxmox-source.env`. Migration must back up an existing ignored local
file and never overwrite it.

## Shared behavior

`image-common.sh` should own:

- repository/image/Packer path resolution;
- UTC structured logs, terminal-aware color, phase names, elapsed time, and a
  final PASS/FAIL/INTERRUPTED summary;
- cleanup and signal handling for temporary Packer projects;
- `require_command`, readable-file, nonempty-value, and safe-value validators;
- consistent usage errors and recovery commands; and
- redaction rules: never print API tokens, AWS credentials, environment file
  contents, or full commands containing secrets.

Platform libraries should own:

- Proxmox environment loading, field validation, SSH preflight, reserved-build-
  IP check, template identifiers, and disk policy;
- AWS profile/session diagnosis before any build, verification, or publication,
  distinguishing expired login from configuration, network, authorization, and
  missing-artifact errors;
- one manifest parser returning a validated AMI ID; and
- one Packer project assembler used by both builds and validation tests.

Every command involving a remote system must finish all local input and
credential checks before creating an AMI, replacing a template, or overwriting
an SSM parameter. Errors must identify the missing file/value/tool and the exact
command needed to continue.

## Safety decisions

- `prepare proxmox` remains read-only unless `--apply` is explicit.
- Source replacement still requires both `--apply --replace`.
- `publish aws` requires an explicit CDK environment and prints the selected
  AMI, profile, region, and CDK-owned destination before writing. `--dry-run`
  performs the complete preflight without changing SSM.
- Aggregate Proxmox builds are sequential across dependency boundaries and
  never invoke Terraform or `rehearsal build`.
- Existing manifest paths, Packer builder targets, VMIDs, disk limits, image
  lineage, and automatic post-build verification remain unchanged.
- AWS login may be offered only after STS confirms an expired or missing login;
  other AWS errors fail with their original category.
- No deletion or replacement target may be derived from an empty variable.

## Implementation phases

### Phase 1: Freeze behavior with tests

1. Extend `infra/tests/images/` to record dispatcher-neutral contracts for all
   current commands: arguments, selected Packer target, validation chaining,
   source preflight/apply/replace behavior, manifest parsing, and SSM publish
   arguments.
2. Add fake `packer`, `ssh`, `aws`, `jq`, and `ping` binaries so command routing
   and failure behavior are testable without live infrastructure.
3. Record executable modes and current manifest/config paths.

Exit: tests fail if any current safety check or target selection is removed.

### Phase 2: Introduce dispatcher and common libraries

1. Add `scripts/image`, global help, subcommand help, common logging, cleanup,
   and summary behavior.
2. Extract the Packer flat-project assembler without changing its arguments or
   generated links.
3. Add shared Proxmox config and AWS session/artifact libraries.
4. Route `doctor` and validate-only commands first because they are
   non-mutating.

Exit: all read-only commands work through the dispatcher and tests prove
missing-input recovery messages.

### Phase 3: Migrate build and mutation commands

1. Route the four Packer build targets through a table-driven build command.
2. Split workstation-side source preparation from the streamed PVE-host script,
   preserving the existing two-step preflight/apply contract.
3. Route AWS publication through the common artifact/session code.
4. Add `build proxmox all`, phase summaries, and failure-resume guidance.

Exit: each old executable and its target command produce equivalent Packer,
SSH, AWS, and verification calls under mocks; live operations remain opt-in.

### Phase 4: Cut over and remove legacy entry points

1. Update tests, active CI/workflows, deployment references, and canonical docs
   to call `scripts/image`.
2. Move `.env.example` and the source bootstrap asset, preserving any ignored
   local `.env` through an explicit backup/migration step.
3. Delete the nine legacy public executables and rename
   `packer-build.sh` to the internal `packer-project.sh` library.
4. Add a structural assertion that `scripts/image` is the only executable shell
   file directly under `infra/images/scripts/`.

Exit: a repository-wide active-reference search finds no legacy command names.

### Phase 5: Documentation and generated outputs

Create `infra/images/README.md` as the operator landing page. It should contain:

1. the image lineage and the boundary between image construction and deployment;
2. a five-minute setup for Packer, Proxmox config, AWS config, and authentication;
3. the common command matrix and the two-command full Proxmox rebuild;
4. which commands are read-only, costly, mutating, or destructive;
5. artifact/manifests and VMID outputs;
6. color/logging controls and final-report examples;
7. failure recovery for missing config, expired AWS login, occupied build IP,
   stale/missing source template, Packer failure, and disk-policy violation; and
8. links to `IMAGE-CONTRACT.md`, `packer/README.md`, tests, and deployment docs.

Update rather than duplicate details in [[machine-image-building|Machine image
building]], [[packer|Packer implementation]], [[scripts|Scripts
implementation]], the scripts/configuration catalogues, Proxmox setup docs, and
deployment READMEs. Regenerate generated repository/index files through their
generator; never edit `docs/90-generated/` manually.

Exit: the root README is sufficient for routine operation and canonical docs no
longer teach legacy filenames.

## Validation matrix

Required before completion:

```bash
bash -n infra/images/scripts/image infra/images/scripts/image-common.sh \
  infra/images/scripts/lib/*.sh
infra/tests/images/validate.sh
python3 scripts/docs/validate-doc-links.py
python3 scripts/docs/validate-doc-metadata.py
git diff --check
```

Also require:

- `packer fmt -check -recursive infra/images/packer`;
- validate-only runs for AWS golden, Proxmox golden, LocalStack fixture, and DB
  fixture targets;
- mocked tests for every public command and negative credential/config path;
- a repository-wide legacy-reference search; and
- explicit live smoke tests, when authorized, for Proxmox source preflight,
  one Proxmox validate-only build, AWS verification, and publication dry-run.

Do not claim a live image build unless Packer actually creates and verifies the
artifact. Structural and mocked validation must be reported separately.

## Decisions to confirm at implementation start

The plan recommends these defaults:

1. `infra/images/scripts/image` is the sole public entry point; no compatibility
   wrappers remain after cutover.
2. The shell-specific Proxmox config moves to
   `infra/images/config/proxmox-source.env`; Packer HCL variables do not move.
3. AWS publication gains a non-mutating `--dry-run`; its environment selects
   the destination through the CDK configuration contract.
4. `build proxmox all` does not implicitly create or replace source template
   `8999`.

Any change to these defaults should be decided before Phase 2 so command names,
tests, and documentation do not churn mid-migration.

## Exit criteria

- One documented operator entry point covers preparation, build, verification,
  artifact inspection, and publication.
- All prechecks and recovery messages are centralized and secrets remain
  redacted.
- The full Proxmox lineage and AWS golden build have clear aggregate commands
  with final reports.
- Legacy executable scripts and active references are removed.
- Packer targets, artifact locations, VMIDs, disk policies, and deployment
  boundaries remain behaviorally unchanged.
- The root image README and canonical docs match the implemented commands.
- Tests, Packer validation, documentation validation, and the agreed live smoke
  tests pass.

## Related documents

- [[70-planning/active/README|Active plans]]
- [[machine-image-building|Machine image building]]
- [[packer|Packer implementation]]
- [[scripts|Scripts implementation]]
