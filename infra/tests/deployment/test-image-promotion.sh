#!/usr/bin/env bash
set -Eeuo pipefail

# Proves that image promotion writes one complete manifest per host role,
# pinned by digest rather than tag.

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPT="${REPO_ROOT}/infra/deployment/aws/scripts/publish-staging-images.sh"
HOST_CONTRACT="${REPO_ROOT}/infra/contracts/runtime-hosts.json"
TEST_DIR="$(mktemp -d)"
trap 'rm -rf "${TEST_DIR}"' EXIT

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

write_manifest() {
  cat > "${TEST_DIR}/release.json" <<'EOF'
{
  "schema_version": 1,
  "commit_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
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
  DRY_RUN=1 RELEASE_MANIFEST_PATH="${TEST_DIR}/release.json" FLOWFORM_ENVIRONMENT=staging \
    bash "${SCRIPT}" promote
}

write_manifest
output="$(run_promote)" || fail "promote exited non-zero"

# Exactly the two role parameters declared by the host contract.
app_parameter="/flowform/staging/app/release"
proxy_parameter="/flowform/staging/proxy/release"
grep -q "would set ${app_parameter}=" <<<"${output}" \
  || fail "missing App release parameter"
grep -q "would set ${proxy_parameter}=" <<<"${output}" \
  || fail "missing Proxy release parameter"
actual_count="$(grep -c 'DRY_RUN: would set' <<<"${output}")"
(( actual_count == 2 )) || fail "expected two role manifests, got ${actual_count}"

for role in app proxy; do
  expected="$(
    jq -r --arg role "${role}" '.roles[$role].release_parameter' "${HOST_CONTRACT}"
  )"
  expected="${expected//\{environment\}/staging}"
  grep -q "would set ${expected}=" <<<"${output}" \
    || fail "${role} parameter does not match the host contract"
done

app_value="$(sed -n "s|^DRY_RUN: would set ${app_parameter}=||p" <<<"${output}")"
proxy_value="$(sed -n "s|^DRY_RUN: would set ${proxy_parameter}=||p" <<<"${output}")"

jq -e '
  .schema_version == 1
  and .source_commit == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  and (.images | keys | sort) == ["alloy", "backend"]
  and ([.images[] | contains("@sha256:")] | all)
' <<<"${app_value}" >/dev/null || fail "App release manifest is invalid"
jq -e '
  .schema_version == 1
  and .source_commit == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  and (.images | keys | sort) == ["alloy", "caddy", "squid"]
  and ([.images[] | contains("@sha256:")] | all)
' <<<"${proxy_value}" >/dev/null || fail "Proxy release manifest is invalid"

app_alloy="$(jq -r '.images.alloy' <<<"${app_value}")"
proxy_alloy="$(jq -r '.images.alloy' <<<"${proxy_value}")"
[[ "${app_alloy}" == "${proxy_alloy}" ]] \
  || fail "Alloy digest differs between the App and Proxy manifests"

# A malformed digest must stop promotion rather than publish a bad reference.
sed 's/sha256:1111111111111111111111111111111111111111111111111111111111111111/not-a-digest/' \
  "${TEST_DIR}/release.json" > "${TEST_DIR}/bad.json"
if DRY_RUN=1 RELEASE_MANIFEST_PATH="${TEST_DIR}/bad.json" FLOWFORM_ENVIRONMENT=staging \
     bash "${SCRIPT}" promote >/dev/null 2>&1; then
  fail "promote accepted an invalid digest"
fi

# A digest-qualified target must agree with the separately recorded digest.
sed '0,/sha256:1111111111111111111111111111111111111111111111111111111111111111/s//sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/' \
  "${TEST_DIR}/release.json" > "${TEST_DIR}/mismatch.json"
if DRY_RUN=1 RELEASE_MANIFEST_PATH="${TEST_DIR}/mismatch.json" FLOWFORM_ENVIRONMENT=staging \
     bash "${SCRIPT}" promote >/dev/null 2>&1; then
  fail "promote accepted a target/digest mismatch"
fi

printf 'PASS: image promotion writes two digest-pinned role manifests\n'
