#!/usr/bin/env bash
set -Eeuo pipefail

# Verify repository ownership and the exact staged-to-installed role layout.

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
IMAGE_ROOT="${REPO_ROOT}/infra/machine-images"
RUNTIME_ROOT="${REPO_ROOT}/infra/containers/runtime"
INSTALL="${IMAGE_ROOT}/shared/provisioners/install-role-assets.sh"
VERIFY_ROLE="${IMAGE_ROOT}/shared/provisioners/verify-role.sh"
VERIFY_BASE="${IMAGE_ROOT}/definitions/base/provisioners/verify-base.sh"

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

for role in app proxy; do
  build="${IMAGE_ROOT}/definitions/${role}/build.pkr.hcl"
  unit="${IMAGE_ROOT}/definitions/${role}/host-assets/systemd/flowform-${role}.service"
  bootstrap="${IMAGE_ROOT}/definitions/${role}/host-assets/bin/bootstrap-${role}.sh"
  compose="${RUNTIME_ROOT}/aws/common/compose/${role}.yml"

  [[ -f "${build}" ]] || fail "missing ${role} Packer definition"
  [[ -x "${bootstrap}" ]] || fail "missing executable ${role} host bootstrap"
  [[ -f "${unit}" ]] || fail "missing ${role} systemd unit"
  [[ -f "${compose}" ]] || fail "missing runtime-owned ${role} Compose topology"

  grep -Fq 'infra/containers/runtime/common/.' "${build}" \
    || fail "${role} Packer build does not stage common runtime assets"
  grep -Fq "infra/containers/runtime/aws/common/compose/${role}.yml" "${build}" \
    || fail "${role} Packer build does not stage runtime-owned Compose topology"
  grep -Fq '/opt/flowform/runtime/common/scripts/run-role.sh' "${unit}" \
    || fail "${role} unit does not invoke runtime convergence"
  grep -Fq "/opt/flowform/runtime/compose/${role}.yml" "${bootstrap}" \
    || fail "${role} bootstrap does not use installed runtime Compose"
done

if find "${IMAGE_ROOT}" -type f \( -name 'compose*.yml' -o -name 'docker-compose*.yml' \) \
  | grep -q .; then
  fail "machine-images owns a Compose file"
fi

for script in load-release-manifest.sh run-role.sh; do
  [[ -x "${RUNTIME_ROOT}/common/scripts/${script}" ]] \
    || fail "runtime helper is missing or non-executable: ${script}"
done
for script in aws-cli-retry.sh bootstrap-common.sh load-instance-context.sh; do
  [[ -x "${IMAGE_ROOT}/shared/host-assets/bin/${script}" ]] \
    || fail "shared host helper is missing or non-executable: ${script}"
done

grep -Fq 'runtime-compose' "${INSTALL}" \
  || fail "role installer does not install runtime-owned Compose"
grep -Fq '/opt/flowform/runtime/common/scripts/run-role.sh' "${VERIFY_ROLE}" \
  || fail "role verifier does not check runtime convergence"
grep -Fq 'test ! -e /opt/flowform/runtime' "${VERIFY_BASE}" \
  || fail "base verifier does not reject role runtime assets"

for forbidden in \
  "${IMAGE_ROOT}/app" \
  "${IMAGE_ROOT}/proxy" \
  "${IMAGE_ROOT}/base" \
  "${IMAGE_ROOT}/scripts"; do
  [[ ! -e "${forbidden}" ]] || fail "stale machine-image path remains: ${forbidden}"
done

printf 'PASS: machine-image and container-runtime ownership boundaries are consistent\n'
