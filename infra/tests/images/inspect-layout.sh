#!/usr/bin/env bash
set -Eeuo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
packer_root="${repo_root}/images/packer"
required=(
  required_plugins.pkr.hcl variables.pkr.hcl locals.pkr.hcl builds.pkr.hcl
  proxmox.pkr.hcl aws.pkr.hcl
  ../provisioning/common/lib.sh
  ../provisioning/common/install-base.sh ../provisioning/common/install-docker.sh
  ../provisioning/common/install-aws-cli.sh ../provisioning/common/configure-host.sh
  ../provisioning/common/verify-image.sh ../provisioning/common/cleanup-image.sh
  ../provisioning/proxmox/install-qemu-agent.sh ../provisioning/proxmox/configure-proxmox-guest.sh
  ../provisioning/aws/configure-ec2.sh ../provisioning/aws/configure-ssm.sh
)
for path in "${required[@]}"; do
  [[ -e "${packer_root}/${path}" ]] || { echo "missing ${path}" >&2; exit 1; }
done
while IFS= read -r script; do
  [[ -x "${script}" ]] || { echo "not executable: ${script}" >&2; exit 1; }
  if LC_ALL=C grep -q $'\r$' "${script}"; then
    echo "CRLF line endings: ${script}" >&2
    exit 1
  fi
done < <(find "${repo_root}/images" "${repo_root}/proxmox" "${repo_root}/runtime" "${repo_root}/tests" -type f -name '*.sh' -print)
printf 'image layout OK\n'
