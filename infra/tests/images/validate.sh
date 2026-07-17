#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
image_root="${repo_root}/images"
tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT

packer fmt -check -recursive "${image_root}/packer"

cp "${image_root}/packer/variables/aws.auto.pkrvars.hcl.example" "${tmp}/aws.pkrvars.hcl"
cp "${image_root}/packer/variables/proxmox.auto.pkrvars.hcl.example" "${tmp}/proxmox.pkrvars.hcl"

# shellcheck source=../../images/scripts/lib/packer-build.sh
. "${image_root}/scripts/lib/packer-build.sh"
PACKER_VALIDATE_ONLY=1 run_packer_build \
  "${image_root}/packer/builds/golden.pkr.hcl" \
  "flowform-golden.amazon-ebs.amazon_linux_2023" \
  "${tmp}/aws.pkrvars.hcl"
PACKER_VALIDATE_ONLY=1 run_packer_build \
  "${image_root}/packer/builds/golden.pkr.hcl" \
  "flowform-golden.proxmox-clone.amazon_linux_2023" \
  "${tmp}/proxmox.pkrvars.hcl"
PACKER_VALIDATE_ONLY=1 run_packer_build \
  "${image_root}/packer/builds/localstack-fixture.pkr.hcl" \
  "flowform-localstack-fixture.proxmox-clone.localstack_fixture" \
  "${tmp}/proxmox.pkrvars.hcl"

"${repo_root}/tests/images/test-prepare-proxmox-source.sh"
"${repo_root}/tests/images/test-verify-aws-ami.sh"

grep -Fq 'qemu_agent      = false' "${image_root}/packer/sources/proxmox.pkr.hcl"
grep -Fq 'clone_vm             = var.proxmox_golden_template' "${image_root}/packer/sources/proxmox.pkr.hcl"
grep -Fq 'compose.localstack.yml' "${image_root}/packer/builds/localstack-fixture.pkr.hcl"
grep -Fq 'docker pull' "${image_root}/packer/provisioners/proxmox/localstack/preload-images.sh"
grep -Fq 'al2023-ami-minimal-' "${image_root}/packer/variables/aws.pkr.hcl"
grep -Fq 'default = 10' "${image_root}/packer/variables/aws.pkr.hcl"
grep -Fq 'verify-aws-ami.sh' "${image_root}/scripts/build-aws-image.sh"
grep -Fq 'PROXMOX_SOURCE_DISK_SIZE=native' "${image_root}/scripts/.env.example"
grep -Fq 'PROXMOX_DISK_MAX_SIZE=25G' "${image_root}/scripts/.env.example"
grep -Fq 'verify-proxmox-disk-sizes.sh' "${image_root}/scripts/build-proxmox-image.sh"
grep -Fq 'verify-proxmox-disk-sizes.sh' "${image_root}/scripts/build-proxmox-localstack-fixture.sh"
! grep -Rq 'install-qemu-agent.sh' "${image_root}/packer"

for script in \
  "${image_root}"/scripts/*.sh \
  "${image_root}"/scripts/lib/*.sh \
  "${image_root}"/packer/provisioners/common/*.sh \
  "${image_root}"/packer/provisioners/aws/*.sh \
  "${image_root}"/packer/provisioners/proxmox/*.sh \
  "${image_root}"/packer/provisioners/proxmox/localstack/*.sh; do
  bash -n "${script}"
done
