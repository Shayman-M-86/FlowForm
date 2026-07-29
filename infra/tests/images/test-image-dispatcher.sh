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
grep -Fq -- '--diagnose-ssh' <<<"${infra_build_help}"
grep -Fq -- '--on-error MODE' <<<"${infra_build_help}"

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

echo 'image dispatcher tests OK'
