# Rehearsal environment

Rehearsal owns only the local values, Compose overrides, and fixtures that make
the Proxmox topology behave like a FlowForm deployment without AWS services.
It does not own VM creation or image construction.

1. Build the shared Proxmox golden template from `infra/image-factory/packer`.
2. Prepare and start VMs with:

   ```bash
   infra/platforms/proxmox/setup-host.sh
   infra/platforms/proxmox/create-vms.sh --force
   ```

3. Use this directory's LocalStack, registry, TLS-shim, Caddy, and Squid
   fixtures to supply rehearsal-only topology and values.

The VMs receive cloud-init from `infra/runtime/cloud-init`, which invokes shared
bootstrap scripts and Compose files from `infra/runtime`. This keeps the
runtime contract identical while allowing rehearsal fixtures to replace
cloud-only dependencies.
