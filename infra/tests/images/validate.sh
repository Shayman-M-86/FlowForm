#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
image_root="${repo_root}/images"
tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT

packer fmt -check -recursive "${image_root}/packer"

cp "${image_root}/packer/variables/aws.auto.pkrvars.hcl.example" "${tmp}/aws.pkrvars.hcl"
cp "${image_root}/packer/variables/proxmox.auto.pkrvars.hcl.example" "${tmp}/proxmox.pkrvars.hcl"

# shellcheck source=../../images/scripts/image-common.sh
. "${image_root}/scripts/image-common.sh"
# shellcheck source=../../images/scripts/lib/packer-project.sh
. "${image_root}/scripts/lib/packer-project.sh"
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
PACKER_VALIDATE_ONLY=1 run_packer_build \
  "${image_root}/packer/builds/db-fixture.pkr.hcl" \
  "flowform-db-fixture.proxmox-clone.db_fixture" \
  "${tmp}/proxmox.pkrvars.hcl"

"${repo_root}/tests/images/test-prepare-proxmox-source.sh"
"${repo_root}/tests/images/test-verify-aws-ami.sh"
"${repo_root}/tests/images/test-image-dispatcher.sh"

grep -Fq 'qemu_agent      = false' "${image_root}/packer/sources/proxmox.pkr.hcl"
grep -Fq 'clone_vm             = var.proxmox_golden_template' "${image_root}/packer/sources/proxmox.pkr.hcl"
grep -Fq 'compose.localstack.yml' "${image_root}/packer/builds/localstack-fixture.pkr.hcl"
grep -Fq 'docker pull' "${image_root}/packer/provisioners/proxmox/localstack/preload-images.sh"
grep -Fq 'compose/db.yml' "${image_root}/packer/builds/db-fixture.pkr.hcl"
grep -Fq 'docker pull' "${image_root}/packer/provisioners/proxmox/db/preload-image.sh"
grep -Fq 'die()' "${image_root}/packer/provisioners/common/lib.sh"
grep -Fq 'al2023-ami-minimal-' "${image_root}/packer/variables/aws.pkr.hcl"
grep -Fq 'default = 10' "${image_root}/packer/variables/aws.pkr.hcl"
grep -Fq 'verify AWS AMI for CDK consumption' "${image_root}/scripts/lib/cmd_build.sh"
grep -Fq 'PROXMOX_SOURCE_DISK_SIZE=native' "${image_root}/config/proxmox-source.env.example"
grep -Fq 'PROXMOX_DISK_MAX_SIZE=25G' "${image_root}/config/proxmox-source.env.example"
grep -Fq '_image_build_proxmox_target golden' "${image_root}/scripts/lib/cmd_build.sh"
grep -Fq '_image_build_proxmox_target localstack' "${image_root}/scripts/lib/cmd_build.sh"
grep -Fq '_image_build_proxmox_target db' "${image_root}/scripts/lib/cmd_build.sh"
grep -Fq 'image_cdk_ami_parameter' "${image_root}/scripts/lib/cmd_publish.sh"
[[ -x "${image_root}/scripts/image" ]]
[[ "$(find "${image_root}/scripts" -maxdepth 1 -type f -perm /111 -printf '%f\n')" == image ]]
for legacy in build-aws-image.sh build-proxmox-image.sh build-proxmox-localstack-fixture.sh \
  build-proxmox-db-fixture.sh prepare-proxmox-source.sh verify-proxmox-disk-sizes.sh \
  verify-aws-ami.sh extract-aws-ami-id.sh publish-aws-ami.sh; do
  [[ ! -e "${image_root}/scripts/${legacy}" ]]
done
! grep -Rq 'install-qemu-agent.sh' "${image_root}/packer"

for script in \
  "${image_root}"/scripts/image \
  "${image_root}"/scripts/image-common.sh \
  "${image_root}"/scripts/lib/*.sh \
  "${image_root}"/scripts/lib/actions/*.sh \
  "${image_root}"/packer/provisioners/common/*.sh \
  "${image_root}"/packer/provisioners/aws/*.sh \
  "${image_root}"/packer/provisioners/proxmox/*.sh \
  "${image_root}"/packer/provisioners/proxmox/localstack/*.sh \
  "${image_root}"/packer/provisioners/proxmox/db/*.sh; do
  bash -n "${script}"
done
