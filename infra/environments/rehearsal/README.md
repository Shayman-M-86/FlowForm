# Rehearsal environment

Rehearsal owns only the local values, Compose overrides, and fixtures that make
the Proxmox topology behave like a FlowForm deployment without AWS services.
It does not own VM creation or image construction.

1. Build and smoke-verify an immutable Proxmox template through
   `infra/image-factory/build-proxmox-template.sh`.
2. On an internet-connected Linux/WSL builder, prepare and upload the pinned
   offline image bundle:

   ```bash
   infra/environments/rehearsal/prepare-artifacts.sh --upload root@pve.example.lan
   ```

3. On Proxmox, create the stopped topology and activate it:

   ```bash
   infra/platforms/proxmox/setup-host.sh
   infra/platforms/proxmox/create-vms.sh --image-manifest /path/to/image-manifest.json
   infra/environments/rehearsal/activate.sh --artifact-manifest /path/to/artifact-manifest.json
   infra/environments/rehearsal/verify.sh
   ```

Activation starts proxy, fixtures, and app in dependency order; loads images
without internet access on the fixtures VM; seeds fake AWS; applies the base and
rehearsal Compose files; and stops on bounded health failures before starting
downstream services.

The VMs receive cloud-init from `infra/runtime/cloud-init`, which invokes shared
bootstrap scripts and Compose files from `infra/runtime`. This keeps the
runtime contract identical while allowing rehearsal fixtures to replace
cloud-only dependencies.
