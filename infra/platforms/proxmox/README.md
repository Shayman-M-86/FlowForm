# Proxmox platform orchestration

This directory owns Proxmox host and VM lifecycle operations: bridge setup,
cloud-init snippet installation, VM cloning, and VM destruction. It does not
construct images.

Build the shared golden template through the machine-image pipeline first:

```bash
infra/image-factory/build-proxmox-template.sh
```

Then, on the Proxmox host, create the rehearsal topology:

```bash
./setup-host.sh
./create-vms.sh --force
```

`create-vms.sh` renders `infra/runtime/cloud-init` templates and attaches them
as Proxmox snippets before boot. Environment-specific values and fixtures remain
under `infra/environments/rehearsal`; the rendered cloud-init starts shared
runtime bootstrap and Compose files.

The defaults clone golden template `9000` for proxy, app, LocalStack, and the
optional development box. No rehearsal-specific image-baking wrapper remains.
