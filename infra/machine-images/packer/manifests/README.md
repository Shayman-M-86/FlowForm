# Image manifests

Packer writes generated manifests here:

- `base-manifest.json`
- `app-manifest.json`
- `proxy-manifest.json`
- `localstack-fixture-manifest.json`
- `db-fixture-manifest.json`

Generated `*.json` files are ignored, but the directory is retained as a stable
tooling contract. Successful AWS verification augments the selected manifest
with the resolved AMI, root snapshot, role, region, architecture, and exact
parent Base AMI where applicable.

The Proxmox fixture manifests remain separate so template `9001` and `9002`
lineage and preloaded-image ownership do not overlap.
