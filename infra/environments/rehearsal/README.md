# Rehearsal environment

Rehearsal is a local execution of the same image and runtime model used by AWS.
It keeps only local topology, local values and local-only fixtures here.
Reusable image construction lives in `infra/images`, shared runtime bootstrap and
Compose files live in `infra/runtime`, and Proxmox VM orchestration lives in
`infra/proxmox`.

## Local workflow

1. Build or update the shared Proxmox image from `infra/images/packer`.
2. Prepare the Proxmox host and clone runtime VMs:

   ```bash
   infra/proxmox/setup-host.sh
   infra/proxmox/create-vms.sh --force
   ```

3. Use the fixtures in this directory for LocalStack, the private registry,
   rehearsal Squid allow-list overrides, and the throwaway TLS shim CA.

The app and proxy VMs receive environment-specific cloud-init values, then run
the shared `infra/runtime/bootstrap` scripts and shared `infra/runtime/compose`
files. The rehearsal-only compose overrides in `compose/` swap in local fixture
configuration without changing the shared runtime contract.
