#!/usr/bin/env bash
set -Eeuo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}/images/packer"
packer fmt -check -recursive .
packer init .
packer validate -syntax-only .
"${repo_root}/tests/images/test-prepare-proxmox-source.sh"

grep -Fq 'qemu_agent      = false' source.proxmox.pkr.hcl
grep -Fq 'ssh_host                = split("/", var.proxmox_build_ip_cidr)[0]' source.proxmox.pkr.hcl
! grep -Rq 'install-qemu-agent.sh' . ../common ../proxmox
