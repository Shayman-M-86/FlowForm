#!/usr/bin/env bash
set -Eeuo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
packer_root="${repo_root}/image-factory/packer"
required=(
  required_plugins.pkr.hcl variables.common.pkr.hcl variables.aws.pkr.hcl variables.proxmox.pkr.hcl
  locals.pkr.hcl build.golden.pkr.hcl source.proxmox.pkr.hcl source.aws.pkr.hcl
  ../provisioners/common/lib.sh
  ../provisioners/common/install-base.sh ../provisioners/common/install-docker.sh
  ../provisioners/common/install-aws-cli.sh ../provisioners/common/configure-host.sh
  ../provisioners/common/verify-image.sh ../provisioners/common/cleanup-image.sh
  ../provisioners/proxmox/install-qemu-agent.sh ../provisioners/proxmox/configure-proxmox-guest.sh
  ../provisioners/aws/configure-ec2.sh ../provisioners/aws/configure-ssm.sh
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
done < <(find "${repo_root}/image-factory" "${repo_root}/platforms/proxmox" "${repo_root}/runtime" "${repo_root}/tests" -type f -name '*.sh' -print)
printf 'image layout OK\n'
