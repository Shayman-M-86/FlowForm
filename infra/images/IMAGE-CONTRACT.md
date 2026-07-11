# FlowForm machine image contract

The Packer image is shared by AWS and local Proxmox rehearsal. It is an Amazon
Linux 2023 host image that guarantees the following build-time state:

- base OS packages needed by runtime bootstrap (`ca-certificates`, `curl`, `jq`,
  `unzip`, `gnupg2`, `nftables`, `openssl`)
- Docker Engine, containerd, Docker CLI, Docker Buildx and Docker Compose plugin
- AWS CLI v2
- `/opt/flowform`, `/etc/flowform` and `/var/lib/flowform`
- common sysctl and cloud-init defaults that keep first boot from doing package
  upgrades or large package installs
- platform agent support: qemu guest agent on Proxmox, SSM Agent on AWS
- validation checks proving the above tools are present
- cleanup of package caches, cloud-init logs and machine identity

The image must not contain application code, application container images,
secrets, `.env` files, TLS private keys for real environments, registry
credentials, AWS credentials, mutable hostnames, or environment-specific IPs.

Runtime orchestration supplies everything environment-specific:

- Proxmox or CDK creates the instance and supplies platform-specific user data
- cloud-init sets hostname/network identity and writes runtime files
- shared `infra/runtime/bootstrap/*` scripts retrieve parameters/secrets and
  start shared `infra/runtime/compose/*` Compose files
- `infra/environments/<env>/` supplies only values, local topology, and local-only
  fixtures such as LocalStack or rehearsal TLS material
