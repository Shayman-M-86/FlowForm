#!/usr/bin/env bash
set -Eeuo pipefail

infra_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
image="${infra_root}/machine-images/tooling/image"
tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT

for command in --help 'build --help' 'prepare --help' 'verify --help' \
  'artifact --help' 'publish --help' 'prune --help' 'doctor --help'; do
  # shellcheck disable=SC2086
  "${image}" ${command} >"${tmp}/help.out" 2>"${tmp}/help.err"
  grep -Fq 'Usage:' "${tmp}/help.out"
done
infra_build_help="$("${image}" build aws --help)"
grep -Fq -- '--diagnostics' <<<"${infra_build_help}"
grep -Fq -- '--no-diagnostics' <<<"${infra_build_help}"
grep -Fq -- '--on-error MODE' <<<"${infra_build_help}"

diagnostic_mode="$(
  INFRA_ROOT="${infra_root}" bash <<'BUILD_MODE_PROBE'
set -Eeuo pipefail
IMAGE_SCRIPT_DIR="${INFRA_ROOT}/machine-images/tooling"
# shellcheck source=../../machine-images/tooling/image-common.sh
source "${IMAGE_SCRIPT_DIR}/image-common.sh"
# shellcheck source=../../machine-images/tooling/lib/cmd_build.sh
source "${IMAGE_SCRIPT_DIR}/lib/cmd_build.sh"
require_vars_file() { :; }
_image_validate_aws_vars() { :; }
image_aws_session_preflight() { :; }
_image_aws_builder_preflight() { :; }
_image_verify_aws() { :; }
run_packer_build() { printf '%s\n' "${PACKER_DIAGNOSTICS}"; }
cmd_build_main aws base
BUILD_MODE_PROBE
)"
[[ "${diagnostic_mode}" == 1 ]]

diagnostic_mode="$(
  INFRA_ROOT="${infra_root}" bash <<'BUILD_MODE_PROBE'
set -Eeuo pipefail
IMAGE_SCRIPT_DIR="${INFRA_ROOT}/machine-images/tooling"
# shellcheck source=../../machine-images/tooling/image-common.sh
source "${IMAGE_SCRIPT_DIR}/image-common.sh"
# shellcheck source=../../machine-images/tooling/lib/cmd_build.sh
source "${IMAGE_SCRIPT_DIR}/lib/cmd_build.sh"
require_vars_file() { :; }
_image_validate_aws_vars() { :; }
image_aws_session_preflight() { :; }
_image_aws_builder_preflight() { :; }
_image_verify_aws() { :; }
run_packer_build() { printf '%s\n' "${PACKER_DIAGNOSTICS}"; }
cmd_build_main aws base --no-diagnostics
BUILD_MODE_PROBE
)"
[[ "${diagnostic_mode}" == 0 ]]

FLOWFORM_OPERATION_ID=test-operation IMAGE_SUBCOMMAND='image test' \
  bash -c 'source "$1"; log "correlated"' _ \
  "${infra_root}/machine-images/tooling/image-common.sh" \
  2>"${tmp}/operation-id.log"
grep -Fq 'operation_id=test-operation' "${tmp}/operation-id.log"

if "${image}" build aws app --on-error invalid \
    >"${tmp}/bad-on-error.out" 2>"${tmp}/bad-on-error.err"; then
  echo 'invalid Packer on-error mode unexpectedly succeeded' >&2
  exit 1
fi
grep -Fq -- '--on-error must be cleanup, abort, or ask' \
  "${tmp}/bad-on-error.err"

cat >"${tmp}/manifest.json" <<'JSON'
{"builds":[{"builder_type":"amazon-ebs","artifact_id":"ap-southeast-2:ami-abc123"}]}
JSON
artifact="$("${image}" artifact aws app --manifest "${tmp}/manifest.json" 2>"${tmp}/artifact.err")"
[[ "${artifact}" == ami-abc123 ]]
grep -Fq 'RESULT: PASS' "${tmp}/artifact.err"

if "${image}" build unknown >"${tmp}/bad.out" 2>"${tmp}/bad.err"; then
  echo 'unknown build platform unexpectedly succeeded' >&2
  exit 1
fi
grep -Fq 'RESULT: FAIL' "${tmp}/bad.err"

IMAGE_SUBCOMMAND='image test' source "${infra_root}/machine-images/tooling/image-common.sh"
[[ "$(image_cdk_ami_parameter dev app)" == /flowform/dev/ec2/appAmiId ]]
[[ "$(image_cdk_ami_parameter staging proxy)" == /flowform/staging/ec2/proxyAmiId ]]
[[ "$(image_cdk_ami_parameter prod base)" == /flowform/prod/ec2/baseAmiId ]]
[[ "$(image_cdk_region)" == ap-southeast-2 ]]
[[ "$(image_cdk_account)" == 908123139858 ]]

unset AWS_PROFILE AWS_DEFAULT_PROFILE
mkdir -p "${tmp}/default-profile-bin"
cat >"${tmp}/default-profile-bin/aws" <<'FAKE_AWS'
#!/usr/bin/env bash
[[ "$*" == *"--profile default"* ]] || exit 1
printf '{"Account":"908123139858"}\n'
FAKE_AWS
chmod +x "${tmp}/default-profile-bin/aws"
PATH="${tmp}/default-profile-bin:${PATH}" IMAGE_SUBCOMMAND='image test' \
  bash -c 'source "$1"; image_aws_session_preflight; [[ "$AWS_PROFILE" == default ]]' _ \
  "${infra_root}/machine-images/tooling/image-common.sh"

mkdir -p "${tmp}/bin"
cat >"${tmp}/bin/aws" <<'FAKE_AWS'
#!/usr/bin/env bash
if [[ "${1:-}" == sts ]]; then
  echo 'ExpiredToken: session expired' >&2
  exit 1
fi
if [[ "${1:-}" == configure && "${2:-}" == get && "${3:-}" == source_profile ]]; then
  profile=''
  while [[ $# -gt 0 ]]; do
    [[ "$1" == --profile ]] && { profile="$2"; break; }
    shift
  done
  [[ "${profile}" == role-profile ]] && printf 'login-profile\n'
  exit 0
fi
exit 1
FAKE_AWS
chmod +x "${tmp}/bin/aws"
if PATH="${tmp}/bin:${PATH}" AWS_PROFILE=role-profile IMAGE_SUBCOMMAND='image test' \
  bash -c 'source "$1"; image_aws_session_preflight' _ \
  "${infra_root}/machine-images/tooling/image-common.sh" >"${tmp}/aws.out" 2>"${tmp}/aws.err"; then
  echo 'expired AWS session unexpectedly passed' >&2
  exit 1
fi
grep -Fq "aws login --profile login-profile" "${tmp}/aws.err"

mkdir -p "${tmp}/packer-bin" "${tmp}/packer-artifacts"
cat >"${tmp}/packer-bin/packer" <<'FAKE_PACKER'
#!/usr/bin/env bash
set -Eeuo pipefail
case "${1:-}" in
  init|validate) exit 0 ;;
  build)
    printf 'live Packer output\n'
    printf 'Packer debug detail\n' >> "${PACKER_LOG_PATH}"
    exit 17
    ;;
  *) exit 2 ;;
esac
FAKE_PACKER
cat >"${tmp}/packer-bin/aws" <<'FAKE_AWS'
#!/usr/bin/env bash
set -Eeuo pipefail
case "$*" in
  *"ec2 describe-instances"*)
    printf 'i-testbuilder\t10.0.0.10\t203.0.113.10\tarn:aws:iam::123456789012:instance-profile/FlowFormPackerBuildProfile\t2026-07-30T00:00:00Z\tsg-test\tsubnet-test\tvpc-test\n'
    ;;
  *"ec2 get-console-output"*) printf 'FlowForm builder console output\n' ;;
  *"ec2 describe-instance-status"*) printf 'running\tok\tok\tok\n' ;;
  *"ssm describe-instance-information"*)
    printf '{"PingStatus":"Online","AgentVersion":"3.3.0"}\n'
    ;;
  *"ssm get-connection-status"*) printf '{"Status":"connected"}\n' ;;
  *) printf '{}\n' ;;
esac
FAKE_AWS
cat >"${tmp}/packer-bin/session-manager-plugin" <<'FAKE_SESSION_MANAGER_PLUGIN'
#!/usr/bin/env bash
printf '1.2.707.0\n'
FAKE_SESSION_MANAGER_PLUGIN
chmod +x "${tmp}/packer-bin/"*
cat >"${tmp}/aws-test.pkrvars.hcl" <<'TEST_VARS'
aws_region = "ap-southeast-2"
TEST_VARS

set +e
PATH="${tmp}/packer-bin:${PATH}" \
  FLOWFORM_OPERATION_ARTIFACT_DIR="${tmp}/packer-artifacts" \
  FLOWFORM_OPERATION_ID="test-packer-operation" \
  INFRA_ROOT="${infra_root}" \
  TEST_VARS_FILE="${tmp}/aws-test.pkrvars.hcl" \
  bash <<'PACKER_FAILURE_PROBE' >"${tmp}/packer-failure.out" 2>&1
set -Eeuo pipefail
IMAGE_SCRIPT_DIR="${INFRA_ROOT}/machine-images/tooling"
# shellcheck source=../../machine-images/tooling/image-common.sh
source "${IMAGE_SCRIPT_DIR}/image-common.sh"
# shellcheck source=../../machine-images/tooling/lib/packer-project.sh
source "${IMAGE_SCRIPT_DIR}/lib/packer-project.sh"
PACKER_DIAGNOSTICS=1 run_packer_build \
  "${INFRA_ROOT}/machine-images/definitions/base/build.pkr.hcl" \
  flowform-base.amazon-ebs.amazon_linux_2023_base \
  "${TEST_VARS_FILE}" \
  -var image_role=base
PACKER_FAILURE_PROBE
packer_failure_status=$?
set -e
[[ "${packer_failure_status}" == 17 ]]
grep -Fq 'live Packer output' "${tmp}/packer-failure.out"
grep -Fq 'requesting a final EC2 status and console-output snapshot' \
  "${tmp}/packer-failure.out"
grep -Fq 'Packer debug log:' "${tmp}/packer-failure.out"
diagnostic_report="$(find "${tmp}/packer-artifacts/packer" -type f -name '*.diagnostics.log' -print -quit)"
debug_report="$(find "${tmp}/packer-artifacts/packer" -type f -name '*.debug.log' -print -quit)"
[[ -n "${diagnostic_report}" && -n "${debug_report}" ]]
[[ "$(stat -c '%a' "${tmp}/packer-artifacts/packer")" == 700 ]]
[[ "$(stat -c '%a' "${diagnostic_report}")" == 600 ]]
[[ "$(stat -c '%a' "${debug_report}")" == 600 ]]
grep -Fq 'operation_id=test-packer-operation' "${diagnostic_report}"
grep -Fq 'final failure snapshot complete' "${diagnostic_report}"
grep -Fq 'Packer debug detail' "${debug_report}"

echo 'image dispatcher tests OK'
