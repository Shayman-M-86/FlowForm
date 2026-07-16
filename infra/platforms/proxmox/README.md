# Proxmox platform orchestration

This directory owns Proxmox host and VM lifecycle operations: bridge setup,
cloud-init snippet installation, VM cloning, and VM destruction. It does not
construct images.

Build and smoke-verify an immutable template through the image factory first.
Its generated manifest is the input to VM creation.

```bash
infra/image-factory/build-proxmox-template.sh --help
```

Then, on the Proxmox host, reconcile prerequisites and create a stopped topology:

```bash
./setup-host.sh
./create-vms.sh --image-manifest /path/to/manifest.json
```

`create-vms.sh` renders cloud-init under `infra/.generated/`, installs snippets,
attaches all requested user data, and leaves every clone stopped. Environment
activation belongs to `infra/environments/rehearsal/activate.sh`, which starts
VMs in dependency order after verifying the offline artifact bundle.

No mutable `9000` default or rehearsal-specific image template exists. The
selected smoke-verified manifest determines the shared template VMID.
