# Proxmox Image and Rehearsal Infrastructure Rework

> Superseded planning snapshot. Do not execute this sequence. The maintained
> topology and workflow are documented in [[Proxmox rehearsal implementation]]
> and the checked-in Packer, Terraform, cloud-init, and container definitions.

## Summary

Rework the infrastructure in two ordered tracks:

1. Make the Packer → Proxmox → rehearsal cold-start workflow reproducible, secure, dependency-ordered, retryable, and verifiable.
2. After operational acceptance, perform the broader behavior-preserving naming and ownership cleanup.

Keep the shared Amazon Linux 2023 golden-image boundary. Do not introduce Ubuntu Autoinstall, bake application images into the golden template, or rely on the undocumented template `9001`.

## Current checkpoint

The local Proxmox rehearsal has reached the Packer-to-Terraform handoff:

- the pinned AL2023 source template and shared golden template `9000` have
  been built through Packer;
- Terraform renders and uploads cloud-init, then owns proxy `210`, app `220`,
  and LocalStack `230` clone lifecycle;
- the proxy completes cloud-init with Caddy and Squid running; and
- the app and LocalStack guests boot with the intended private network shape.

The LocalStack runtime is the current blocker. VM `230` has no default route by
design, but its cloud-init attempts to pull LocalStack and registry images from
Docker Hub. Those pulls fail, so LocalStack, the registry, and TLS shim do not
start. The next work is a Proxmox-only Packer fixture template derived from
shared golden template `9000` and preloaded with the required third-party
images. It must not add application images or mutable runtime state to the
shared golden template.

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

### 2. Offline LocalStack fixture template

- Add a Proxmox-only Packer fixture build that clones shared golden template
  `9000` and preloads the digest-pinned LocalStack, registry, and TLS-shim
  images required by VM `230`.
- Keep the shared golden image free of application images, secrets, and
  environment-specific runtime state.
- Emit a distinct fixture-template VMID/name and record the source golden
  template plus the preloaded image digests in its manifest.
- Update Terraform to use the fixture-template VMID only for LocalStack while
  proxy and app continue to clone the shared golden template.
- Verify the isolated LocalStack VM can start its services without a default
  route or Docker Hub access.

### 3. Separate VM creation from activation

- Update Proxmox host setup to assign `10.10.10.1/24` to `vmbr10`. VMs still receive no default gateway, preserving isolation while allowing host-side orchestration, transfer, and health checks.
- Generate a root-owned rehearsal orchestration SSH key under `/var/lib/flowform/rehearsal/`; inject its public key into every clone and remove the fixed `rehearsal` password.
- Replace host-local VM lifecycle scripts with Terraform. Terraform renders and
  uploads cloud-init from the local checkout, clones the Packer template, and
  owns destroy/recreate through state.
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
- Keep infrastructure image validation under `infra/tests/images/`.
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
infra/images/scripts/image prepare proxmox --apply
infra/images/scripts/image build proxmox all

# Proxmox deployment
host/01-setup-host.sh
terraform/render-cloud-init.sh
terraform plan
terraform apply
terraform destroy
host/01-setup-host.sh --undo
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

- A Proxmox-only Packer fixture template is the selected offline delivery
  mechanism for the LocalStack, registry, and TLS-shim images. The checked-in
  build is implemented; a real fixture build and rehearsal acceptance remain.
- Terraform owns clone lifecycle and starts the configured rehearsal VMs.
- Packer runs through Bash on Linux or WSL; WSL is supported only when preflight proves API and build-VM SSH reachability.
- Golden templates use immutable versioned VMIDs and manifests.
- The Amazon Linux source-template import is automated and checksum-verified.
- The broader naming/ownership cleanup is included but occurs only after the operational workflow passes end-to-end acceptance.
- AWS architecture and deployment logic remain unchanged except where shared image-contract validation requires updates.
