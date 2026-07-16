---
title: Proxmox image and rehearsal infrastructure rework
document_type: planning
status: active
authority: planning
verified_against_commit: null
tags: [infrastructure]
related_code:
  - "../../../infra/image-factory/"
  - "../../../infra/platforms/proxmox/"
  - "../../../infra/environments/rehearsal/"
related_docs:
  - "Proxmox Packer caveats"
---

# Proxmox Image and Rehearsal Infrastructure Rework

Implementation status: source preparation, hardened Packer input/preflight,
immutable manifests, offline artifacts, stopped topology creation, ordered
activation, verification, and local contract tests are implemented in the
working tree. Real Packer and Proxmox acceptance remains required before the
structural cleanup phase begins.

## Summary

Rework the infrastructure in two ordered tracks:

1. Make the Packer → Proxmox → rehearsal cold-start workflow reproducible, secure, dependency-ordered, retryable, and verifiable.
2. After operational acceptance, perform the broader behavior-preserving naming and ownership cleanup.

Keep the shared Amazon Linux 2023 golden-image boundary. Do not introduce Ubuntu Autoinstall, bake application images into the golden template, or rely on the undocumented template `9001`.

## Implementation Changes

### 1. Reproducible Proxmox image pipeline

- Automate importing a pinned official Amazon Linux 2023 qcow2 into Proxmox:
  - Track its release, URL, checksum, source VMID, and source-template name.
  - Verify the checksum before upload.
  - Configure cloud-init, serial console, storage, networking, and `ec2-user`.
  - Refuse to overwrite an existing mismatched source template unless explicitly requested.
- Harden Packer configuration:
  - Require a dedicated least-privilege Proxmox Packer account and token.
  - Remove secret defaults and secret values from `.pkrvars.hcl` examples.
  - Load the one-time token value from `PROXMOX_TOKEN_SECRET_FILE`, exporting it only as `PKR_VAR_proxmox_token_secret`.
  - Validate token format, API connectivity, TLS policy, node, bridge, storage, source template, and permissions before building.
  - Default TLS verification to enabled; permit the lab self-signed bypass only through explicit configuration with a warning.
  - Replace syntax-only validation with variable-aware validation for the selected Proxmox builder.
  - Pin or checksum external installers and record Packer/plugin/tool versions in the build manifest.
- Complete image generalization:
  - Remove machine ID, cloud-init state/logs, temporary credentials, caches, histories, and SSH host keys.
  - Verify Docker, Compose, AWS CLI, cloud-init, and QEMU guest agent before conversion.
  - Confirm cloned VMs regenerate machine identity and SSH host keys.
- Build immutable versioned templates:
  - Require an unused output VMID.
  - Name the template using the source commit and VMID.
  - Emit a FlowForm image manifest containing VMID, name, source-image checksum, source commit, tool versions, build time, and verification result.
  - Smoke-clone every candidate, verify it, destroy the smoke VM, and only then make its manifest selectable by rehearsal.

### 2. Deterministic rehearsal artifacts

- Add a tracked lock describing exact digest-pinned LocalStack, registry, Caddy, and Postgres images.
- Add an internet-connected Linux/WSL artifact preparation command that:
  - Verifies Docker and repository cleanliness or records dirty state explicitly.
  - Pulls the locked third-party images.
  - Builds the backend image and labels/tags it with the Git commit.
  - Produces `rehearsal-images.tar`, `manifest.json`, and `SHA256SUMS`.
  - Uploads the complete artifact set to the configured Proxmox host staging directory.
- The artifact manifest must identify every image digest, backend commit, bundle checksum, and compatible image-template contract version.
- Activation must reject missing, corrupt, or incompatible bundles before starting the app VM.

### 3. Separate VM creation from activation

- Update Proxmox host setup to assign `10.10.10.1/24` to `vmbr10`. VMs still receive no default gateway, preserving isolation while allowing host-side orchestration, transfer, and health checks.
- Generate a root-owned rehearsal orchestration SSH key under `/var/lib/flowform/rehearsal/`; inject its public key into every clone and remove the fixed `rehearsal` password.
- Change `create-vms.sh` to:
  - Require a verified image manifest rather than defaulting to VMID `9000`.
  - Render cloud-init into a generated-output directory.
  - Attach app, proxy, fixtures, and optional development cloud-init correctly.
  - Clone and configure all requested VMs but leave them stopped.
  - Never run environment activation implicitly.
- Update destruction to remove only VMIDs recorded in rehearsal state. Add `--purge-state` to remove generated keys, manifests, bundles, and activation state without requiring manual cleanup.
- Remove stale references to templates `9001`/`9002`, baked fixture images, and the nonexistent verification script.

### 4. Add dependency-ordered activation

Create `infra/environments/rehearsal/activate.sh` as the environment-level orchestrator:

1. Validate the selected template and artifact manifests.
2. Start proxy VM 210 and wait for QEMU agent, cloud-init, Docker, Caddy, and Squid readiness.
3. Start fixtures VM 230 and wait for host/cloud-init preparation.
4. Transfer and verify the OCI bundle, then load all images.
5. Start registry, LocalStack, and TLS shim in explicit order and wait for their health endpoints.
6. Push the bundled Postgres and backend images into the local registry.
7. Run the existing LocalStack seed contract from VM 230 using the manifest-derived backend reference.
8. Start app VM 220 only after dependencies are healthy and seeded.
9. Embed and select both the shared app Compose file and rehearsal override so the local PostgreSQL services are included.
10. Wait for database and backend health, then verify the public path through Caddy.
11. Start VM 240 only with `--with-dev`, with its cloud-init attached.

Use bounded health polling, not fixed sleeps. Every step must be idempotent, log its stage and timeout, probe live state before acting, and leave the app stopped if a prerequisite fails. Rerunning activation after failure or reboot must reconcile the environment safely.

Add `verify.sh` to prove:

- All expected VMs, interfaces, addresses, services, and image versions match the manifests.
- LocalStack and registry are healthy and seeded.
- The app uses both Compose layers and both databases are healthy.
- Backend readiness succeeds directly and through Caddy.
- The app VM has no default route or public internet access.
- Fake AWS traffic succeeds through Squid, TLS shim, and LocalStack.
- No real credentials or environment-specific application artifacts exist in the golden image.

### 5. Complete the structural cleanup after acceptance

Implement as a separate behavior-preserving commit:

- Make environment directories the source of environment inputs; adapters consume them rather than owning them.
- Standardize environment identifiers as `dev`, `rehearsal`, `staging`, and `prod`.
- Move PostgreSQL under `database/postgres/` and update every schema, Compose, backend, script, CI, and documentation reference.
- Rename infrastructure image tests to `tests/image-factory/`.
- Move rendered cloud-init and other generated artifacts under `infra/.generated/`.
- Standardize new Compose names on `compose*.yaml`, normalize README/contract filenames, and remove explicitly legacy experiment files.
- Run a complete reference sweep immediately after moves; do not leave compatibility wrappers once one canonical path exists.

### 6. Documentation

- Replace the untracked `Packer Caveats .MD` with a properly named planning document containing metadata and an applicability table:
  - Retain API credentials, permissions, TLS, SSH, cleanup, cloud-init, validation, clone, and versioning caveats.
  - Mark Ubuntu ISO, NoCloud HTTP-server, boot-command, Autoinstall, APT, and manual-installer caveats as inapplicable to the Amazon Linux clone builder.
- Add a verified Proxmox rehearsal workflow covering command locations, prerequisites, failure stages, artifact preparation, activation, verification, recovery, and teardown.
- Update canonical deployment/repository documentation only after implementation is verified.
- Run `get_impacted_docs`, review high-confidence results, regenerate generated documentation, and run both documentation validators.

## Command Interfaces

```text
# Linux/WSL build host
prepare-proxmox-source.sh --source-vmid ID
build-proxmox-template.sh --vmid ID --var-file FILE
prepare-artifacts.sh --release GIT_SHA --upload PVE_SSH_TARGET

# Proxmox host
setup-host.sh
create-vms.sh --image-manifest FILE [--with-dev]
activate.sh --artifact-manifest FILE [--with-dev]
verify.sh
destroy-vms.sh [--purge-state]
setup-host.sh --undo
```

All commands must support `--help`, validate prerequisites before mutation, avoid printing secrets, and return nonzero on incomplete work.

## Test Plan

- Add plain Bash tests with fake `qm`, `pvesm`, `ssh`, `scp`, `curl`, and Docker executables to assert command ordering and failure behavior without requiring Proxmox.
- Test missing credentials, invalid token format, TLS failure, insufficient permission, absent source template, occupied output VMID, checksum failure, corrupt artifact bundle, health timeout, seed failure, registry failure, and backend failure.
- Assert that VM creation attaches all expected cloud-init snippets and performs no `qm start`.
- Assert that activation never starts VM 220 before registry population and LocalStack seeding.
- Validate shell syntax, executable modes, line endings, Packer formatting, full variable-aware Packer validation, rendered cloud-init placeholders, Compose merges, and documentation links/metadata.
- On real Proxmox, run:
  - source import;
  - candidate build and smoke clone;
  - clean topology creation;
  - first activation;
  - idempotent second activation;
  - fixtures/app reboot followed by recovery activation;
  - isolation verification;
  - teardown and clean recreation.

Acceptance requires a clean rehearsal to become healthy without manually rerunning bootstrap, seeding, loading images, or editing a VM/template.

## Assumptions and Defaults

- OCI bundles are the chosen offline image-delivery mechanism.
- `create-vms.sh` leaves every clone stopped.
- Packer runs through Bash on Linux or WSL; WSL is supported only when preflight proves API and build-VM SSH reachability.
- Golden templates use immutable versioned VMIDs and manifests.
- The Amazon Linux source-template import is automated and checksum-verified.
- The broader naming/ownership cleanup is included but occurs only after the operational workflow passes end-to-end acceptance.
- AWS architecture and deployment logic remain unchanged except where shared image-contract validation requires updates.
