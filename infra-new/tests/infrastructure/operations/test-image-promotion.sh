#!/usr/bin/env bash
# TODO(migration): Update paths, contracts, and runtime wiring for infra-new before this file is used.
set -Eeuo pipefail

# Proves that image promotion writes exactly the five runtime image parameters
# the contract declares, pinned by digest rather than tag.

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPT="${REPO_ROOT}/infra/deployment/aws/scripts/publish-staging-images.sh"
CONTRACT="${REPO_ROOT}/infra/deployment/config/runtime-parameter-contract.json"
TEST_DIR="$(mktemp -d)"
trap 'rm -rf "${TEST_DIR}"' EXIT

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

write_manifest() {
  cat > "${TEST_DIR}/release.json" <<'EOF'
{
  "schema_version": 1,
  "commit_sha": "testsha",
  "generated_at": "2026-07-28T00:00:00Z",
  "aws": {"account_id": "000000000000", "region": "ap-southeast-2"},
  "platform": "linux/amd64",
  "images": [
    {"name":"backend","target":"reg/flowform-staging-backend@sha256:1111111111111111111111111111111111111111111111111111111111111111","digest":"sha256:1111111111111111111111111111111111111111111111111111111111111111"},
    {"name":"caddy","target":"reg/flowform-staging-caddy@sha256:2222222222222222222222222222222222222222222222222222222222222222","digest":"sha256:2222222222222222222222222222222222222222222222222222222222222222"},
    {"name":"squid","target":"reg/flowform-staging-squid@sha256:3333333333333333333333333333333333333333333333333333333333333333","digest":"sha256:3333333333333333333333333333333333333333333333333333333333333333"},
    {"name":"alloy","target":"reg/flowform-staging-alloy@sha256:4444444444444444444444444444444444444444444444444444444444444444","digest":"sha256:4444444444444444444444444444444444444444444444444444444444444444"}
  ]
}
EOF
}

run_promote() {
  DRY_RUN=1 RELEASE_MANIFEST_PATH="${TEST_DIR}/release.json" FLOWFORM_SCOPE=nonprod \
    bash "${SCRIPT}" promote
}

write_manifest
output="$(run_promote)" || fail "promote exited non-zero"

# Every image reference must be digest-pinned; a tag reference would let the
# same parameter resolve to different bytes over time.
while IFS= read -r line; do
  value="${line#*=}"
  [[ "${value}" == *"@sha256:"* ]] || fail "not digest-pinned: ${line}"
  [[ "${value}" != *"@sha256@sha256:"* ]] || fail "digest qualifier was duplicated: ${line}"
  [[ "${value}" != *":t@"* ]] || fail "tag was not stripped: ${line}"
done < <(grep 'DRY_RUN: would set' <<<"${output}")

# Exactly the five parameters the contract declares, no more and no fewer.
declare -a expected=(
  "/flowform/nonprod/backend/BACKEND_IMAGE"
  "/flowform/nonprod/backend/ALLOY_IMAGE"
  "/flowform/nonprod/proxy/CADDY_IMAGE"
  "/flowform/nonprod/proxy/SQUID_IMAGE"
  "/flowform/nonprod/proxy/ALLOY_IMAGE"
)
for name in "${expected[@]}"; do
  grep -q "would set ${name}=" <<<"${output}" || fail "missing parameter: ${name}"
done

actual_count="$(grep -c 'DRY_RUN: would set' <<<"${output}")"
(( actual_count == ${#expected[@]} )) \
  || fail "expected ${#expected[@]} parameters, got ${actual_count}"

# The promoted names must exist in the shared contract, or bootstrap would
# never render them into its env file.
for name in "${expected[@]}"; do
  group="$(cut -d/ -f4 <<<"${name}")"
  env_name="$(cut -d/ -f5 <<<"${name}")"
  jq -e --arg g "${group}" --arg n "${env_name}" \
    '.runtime_groups[$g].parameters | to_entries | map(select(.value.name == $n)) | length == 1' \
    "${CONTRACT}" >/dev/null \
    || fail "${env_name} is not declared in the ${group} runtime group"
done

# Alloy runs on both hosts and must resolve to the same digest in both groups.
backend_alloy="$(grep -o '/flowform/nonprod/backend/ALLOY_IMAGE=.*' <<<"${output}")"
proxy_alloy="$(grep -o '/flowform/nonprod/proxy/ALLOY_IMAGE=.*' <<<"${output}")"
[[ "${backend_alloy#*=}" == "${proxy_alloy#*=}" ]] \
  || fail "alloy digest differs between the backend and proxy groups"

# A malformed digest must stop promotion rather than publish a bad reference.
sed 's/sha256:1111111111111111111111111111111111111111111111111111111111111111/not-a-digest/' \
  "${TEST_DIR}/release.json" > "${TEST_DIR}/bad.json"
if DRY_RUN=1 RELEASE_MANIFEST_PATH="${TEST_DIR}/bad.json" FLOWFORM_SCOPE=nonprod \
     bash "${SCRIPT}" promote >/dev/null 2>&1; then
  fail "promote accepted an invalid digest"
fi

# A digest-qualified target must agree with the separately recorded digest.
sed '0,/sha256:1111111111111111111111111111111111111111111111111111111111111111/s//sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/' \
  "${TEST_DIR}/release.json" > "${TEST_DIR}/mismatch.json"
if DRY_RUN=1 RELEASE_MANIFEST_PATH="${TEST_DIR}/mismatch.json" FLOWFORM_SCOPE=nonprod \
     bash "${SCRIPT}" promote >/dev/null 2>&1; then
  fail "promote accepted a target/digest mismatch"
fi

printf 'PASS: image promotion writes 5 digest-pinned contract parameters\n'
