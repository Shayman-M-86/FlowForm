#!/usr/bin/env bash
set -Eeuo pipefail

infra_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
image_root="${infra_root}/machine-images"
tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT

packer fmt -check -recursive "${image_root}"

cp "${image_root}/packer/variables/aws.auto.pkrvars.hcl.example" \
  "${tmp}/aws.pkrvars.hcl"
cp "${image_root}/packer/variables/proxmox.auto.pkrvars.hcl.example" \
  "${tmp}/proxmox.pkrvars.hcl"

# shellcheck source=../../machine-images/tooling/image-common.sh
. "${image_root}/tooling/image-common.sh"
# shellcheck source=../../machine-images/tooling/lib/packer-project.sh
. "${image_root}/tooling/lib/packer-project.sh"

PACKER_VALIDATE_ONLY=1 run_packer_build \
  "${image_root}/definitions/base/build.pkr.hcl" \
  "flowform-base.amazon-ebs.amazon_linux_2023_base" \
  "${tmp}/aws.pkrvars.hcl" \
  -var image_role=base
PACKER_VALIDATE_ONLY=1 run_packer_build \
  "${image_root}/definitions/app/build.pkr.hcl" \
  "flowform-app.amazon-ebs.flowform_role" \
  "${tmp}/aws.pkrvars.hcl" \
  -var image_role=app \
  -var aws_base_ami_id=ami-00000000000000000
PACKER_VALIDATE_ONLY=1 run_packer_build \
  "${image_root}/definitions/proxy/build.pkr.hcl" \
  "flowform-proxy.amazon-ebs.flowform_role" \
  "${tmp}/aws.pkrvars.hcl" \
  -var image_role=proxy \
  -var aws_base_ami_id=ami-00000000000000000
PACKER_VALIDATE_ONLY=1 run_packer_build \
  "${image_root}/definitions/base/build.pkr.hcl" \
  "flowform-base.proxmox-clone.amazon_linux_2023" \
  "${tmp}/proxmox.pkrvars.hcl" \
  -var image_role=base
PACKER_VALIDATE_ONLY=1 run_packer_build \
  "${image_root}/packer/builds/localstack-fixture.pkr.hcl" \
  "flowform-localstack-fixture.proxmox-clone.localstack_fixture" \
  "${tmp}/proxmox.pkrvars.hcl"
PACKER_VALIDATE_ONLY=1 run_packer_build \
  "${image_root}/packer/builds/db-fixture.pkr.hcl" \
  "flowform-db-fixture.proxmox-clone.db_fixture" \
  "${tmp}/proxmox.pkrvars.hcl"

"${infra_root}/tests/images/test-prepare-proxmox-source.sh"
"${infra_root}/tests/images/test-verify-aws-ami.sh"
"${infra_root}/tests/images/test-image-dispatcher.sh"
"${infra_root}/tests/images/test-prune-aws-images.sh"
"${infra_root}/tests/images/test-runtime-assets.sh"

grep -Fq 'qemu_agent      = false' "${image_root}/packer/sources/proxmox.pkr.hcl"
grep -Fq 'clone_vm             = var.proxmox_golden_template' \
  "${image_root}/packer/sources/proxmox.pkr.hcl"
grep -Fq 'runtime/proxmox/rehearsal/fixtures/compose.localstack.yml' \
  "${image_root}/packer/builds/localstack-fixture.pkr.hcl"
grep -Fq 'runtime/proxmox/rehearsal/compose/db.yml' \
  "${image_root}/packer/builds/db-fixture.pkr.hcl"
grep -Fq 'docker pull' \
  "${image_root}/packer/provisioners/proxmox/localstack/preload-images.sh"
grep -Fq 'docker pull' \
  "${image_root}/packer/provisioners/proxmox/db/preload-image.sh"
grep -Fq 'die()' "${image_root}/definitions/base/provisioners/lib.sh"
grep -Fq 'al2023-ami-minimal-' "${image_root}/packer/variables/aws.pkr.hcl"
grep -Fq 'default = 10' "${image_root}/packer/variables/aws.pkr.hcl"
[[ "$(grep -Fc 'ssh_interface             = "session_manager"' \
  "${image_root}/packer/sources/aws.pkr.hcl")" == 2 ]]
[[ "$(grep -Fc 'ssh_clear_authorized_keys = true' \
  "${image_root}/packer/sources/aws.pkr.hcl")" == 2 ]]
[[ "$(grep -Fc 'http_tokens                 = "required"' \
  "${image_root}/packer/sources/aws.pkr.hcl")" == 2 ]]
grep -Fq 'amazon-ssm-ap-southeast-2/latest/linux_amd64/amazon-ssm-agent.rpm' \
  "${image_root}/packer/user-data/aws-builder-diagnostics.sh"
! grep -Fq 'temporary_security_group_source_public_ip' \
  "${image_root}/packer/sources/aws.pkr.hcl"
grep -Fq '_image_build_proxmox_target golden' "${image_root}/tooling/lib/cmd_build.sh"
grep -Fq '_image_build_proxmox_target localstack' "${image_root}/tooling/lib/cmd_build.sh"
grep -Fq '_image_build_proxmox_target db' "${image_root}/tooling/lib/cmd_build.sh"
grep -Fq -- '--role <app|proxy>' "${image_root}/tooling/lib/cmd_publish.sh"
grep -Fq 'parent of protected' "${image_root}/tooling/lib/cmd_prune.sh"

[[ -x "${image_root}/tooling/image" ]]
for path in \
  definitions/base/build.pkr.hcl \
  definitions/app/build.pkr.hcl \
  definitions/proxy/build.pkr.hcl \
  shared/host-assets/bin \
  shared/provisioners \
  tooling/lib; do
  [[ -e "${image_root}/${path}" ]]
done
for stale in base app proxy scripts; do
  [[ ! -e "${image_root}/${stale}" ]]
done

while IFS= read -r script; do
  bash -n "${script}"
done < <(
  find \
    "${image_root}/definitions" \
    "${image_root}/shared" \
    "${image_root}/packer/provisioners" \
    "${image_root}/tooling" \
    "${infra_root}/containers/runtime/common/scripts" \
    -type f -name '*.sh' -print
)
bash -n "${image_root}/tooling/image"

printf 'machine-image validation OK\n'
