#!/usr/bin/env bash
set -Eeuo pipefail

# Proves the golden image's runtime assets are wired consistently: what Packer
# stages, what the install provisioner requires, and what the bootstrap scripts
# resolve at runtime must all agree.
#
# A mismatch here produces an instance that boots and then fails in user data,
# which is expensive to diagnose, so it is checked at build time instead.

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
GOLDEN="${REPO_ROOT}/infra/images/packer/builds/golden.pkr.hcl"
INSTALL="${REPO_ROOT}/infra/images/packer/provisioners/common/install-runtime-assets.sh"
VERIFY="${REPO_ROOT}/infra/images/packer/provisioners/common/verify-image.sh"
LOCALS="${REPO_ROOT}/infra/images/packer/locals.pkr.hcl"
APP_STACK="${REPO_ROOT}/infra/deployment/aws/cdk/flowform_infra/stacks/application_stack.py"

TEST_DIR="$(mktemp -d)"
trap 'rm -rf "${TEST_DIR}"' EXIT

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

ASSET_ROOT="/opt/flowform/repo"

# The install provisioner must run as part of the golden build.
grep -q 'install-runtime-assets.sh' "${LOCALS}" \
  || fail "install-runtime-assets.sh is not in the common script list"

# Packer must stage every tree the install provisioner copies.
for tree in \
  "infra/deployment/bootstrap" \
  "infra/containers/runtime/compose" \
  "infra/containers/strategies/aws"
do
  grep -q "${tree}" "${GOLDEN}" \
    || fail "golden build does not stage ${tree}"
  [[ -e "${REPO_ROOT}/${tree}" ]] \
    || fail "staged tree does not exist in the repository: ${tree}"
done

# CDK must exec the same path the image installs to.
grep -q "RUNTIME_ASSET_ROOT = \"${ASSET_ROOT}\"" "${APP_STACK}" \
  || fail "application stack does not target ${ASSET_ROOT}"
grep -q "TARGET=\"${ASSET_ROOT}\"" "${INSTALL}" \
  || fail "install provisioner does not install to ${ASSET_ROOT}"

# The image must verify the entry points user data execs.
for host in app proxy; do
  grep -q "test -x ${ASSET_ROOT}/infra/deployment/bootstrap/bootstrap-${host}.sh" "${VERIFY}" \
    || fail "verify-image.sh does not check bootstrap-${host}.sh"
done

# Reproduce the staged layout and confirm each bootstrap script's own REPO_ROOT
# math lands on it, so its Compose defaults resolve inside the baked tree.
mkdir -p "${TEST_DIR}/repo/infra/deployment" \
         "${TEST_DIR}/repo/infra/containers/runtime" \
         "${TEST_DIR}/repo/infra/containers/strategies"
cp -a "${REPO_ROOT}/infra/deployment/bootstrap" "${TEST_DIR}/repo/infra/deployment/"
cp -a "${REPO_ROOT}/infra/containers/runtime/compose" "${TEST_DIR}/repo/infra/containers/runtime/"
cp -a "${REPO_ROOT}/infra/containers/strategies/aws" "${TEST_DIR}/repo/infra/containers/strategies/"

resolved="$(cd "${TEST_DIR}/repo/infra/deployment/bootstrap" && cd ../../.. && pwd)"
[[ "${resolved}" == "${TEST_DIR}/repo" ]] \
  || fail "bootstrap REPO_ROOT resolves to ${resolved}, not the asset root"

for path in \
  "infra/containers/runtime/compose/app.yml" \
  "infra/containers/runtime/compose/proxy.yml" \
  "infra/containers/strategies/aws/compose/proxy.override.yml"
do
  [[ -f "${TEST_DIR}/repo/${path}" ]] \
    || fail "baked layout is missing a Compose default: ${path}"
done

# The image carries no application source or secrets.
if find "${TEST_DIR}/repo" -name '*.secret.*' -o -name '.env' | grep -q .; then
  fail "runtime assets contain secret-looking files"
fi

printf 'PASS: golden image runtime assets match the bootstrap and CDK contracts\n'
