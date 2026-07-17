# FlowForm machine image contract

The shared Packer golden image targets AWS and Proxmox. It is an Amazon Linux
2023 host image that guarantees the following build-time state:

- base OS packages needed by runtime bootstrap (`ca-certificates`,
  `curl-minimal`, `jq`, `unzip`, `nftables`, `openssl`)
- Docker Engine, containerd, Docker CLI, Docker Buildx and Docker Compose plugin
- AWS CLI v2
- `/opt/flowform`, `/etc/flowform` and `/var/lib/flowform`
- common sysctl and cloud-init defaults that keep first boot from doing package
  upgrades or large package installs
- SSM Agent support on AWS; Proxmox uses cloud-init and an explicit temporary
  SSH address during image construction because AL2023 does not package a
  supported QEMU guest agent
- validation checks proving the above tools are present
- cleanup of package caches, cloud-init logs and machine identity

The shared golden image must not contain application code, application or
fixture container images, secrets, `.env` files, TLS private keys, registry
credentials, AWS credentials, mutable hostnames, or environment-specific IPs.

The shared contract does not require identical source disks. AWS builds from
the official minimal AL2023 EC2 AMI and uses an encrypted 10 GiB gp3 root;
Proxmox builds from the official KVM QCOW2 and preserves its native 25 GiB
disk. Both run the same common provisioners and verification, followed by only
the platform-specific guest steps. An AWS build must fail if its output AMI or
root snapshot differs from the configured 8–12 GiB policy.

The Proxmox-only LocalStack fixture is the sole container-image exception. It
is derived from the Proxmox golden template and may contain only the image
layers named by the maintained rehearsal LocalStack, registry, and TLS-shim
Compose files, plus a generated inventory/archive of those image layers. This
exception exists only so the isolated LocalStack VM can start offline.

The fixture must not contain Compose files, IP addresses, SSH keys, secrets,
`.env` files, TLS configuration or keys, seeded LocalStack resources, systemd
service units, running containers, or service startup state.

Proxmox templates preserve the official AL2023 QCOW2's native 25 GiB virtual
disk unless an operator explicitly requests and approves a larger size. The
downloaded QCOW2 and completed source, golden, and fixture templates must not
exceed `PROXMOX_DISK_MAX_SIZE`. A size reduction is performed by rebuilding
from the original QCOW2, never by attempting to shrink the XFS filesystem.

Runtime orchestration supplies everything environment-specific:

- Proxmox or CDK creates the instance and supplies platform-specific user data
- cloud-init sets hostname/network identity and writes runtime files
- shared `infra/deployment/bootstrap/*` scripts retrieve parameters/secrets and
  start shared `infra/containers/deployment/compose/*` Compose files
- `infra/containers/<stage>/` and `infra/env/<env>/` supply values, topology,
  Compose definitions, and local-only fixtures such as LocalStack seed data or
  rehearsal TLS material
