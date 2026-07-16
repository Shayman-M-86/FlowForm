#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../../.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT

make_case() {
  local name="$1" root="${tmp}/$1"
  mkdir -p "${root}/bin" "${root}/state/ssh" "${root}/artifacts" "${root}/qm-state"
  printf 'test-only-private-key\n' > "${root}/state/ssh/id_ed25519"
  chmod 0600 "${root}/state/ssh/id_ed25519"

  cat > "${root}/bin/qm" <<'MOCK'
#!/usr/bin/env bash
set -Eeuo pipefail
printf 'qm %s\n' "$*" >> "${MOCK_LOG}"
case "$1" in
  status)
    if [[ -f "${MOCK_QM_STATE}/$2" ]]; then printf 'status: running\n'; else printf 'status: stopped\n'; fi
    ;;
  start) touch "${MOCK_QM_STATE}/$2" ;;
  guest) exit 0 ;;
  *) exit 0 ;;
esac
MOCK
  cat > "${root}/bin/ssh" <<'MOCK'
#!/usr/bin/env bash
printf 'ssh %s\n' "$*" >> "${MOCK_LOG}"
if [[ -n "${MOCK_SSH_FAIL_PATTERN:-}" && "$*" == *"${MOCK_SSH_FAIL_PATTERN}"* ]]; then
  exit 23
fi
exit 0
MOCK
  cat > "${root}/bin/scp" <<'MOCK'
#!/usr/bin/env bash
printf 'scp %s\n' "$*" >> "${MOCK_LOG}"
MOCK
  cat > "${root}/bin/ssh-keyscan" <<'MOCK'
#!/usr/bin/env bash
printf 'host ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITestOnlyKey\n'
MOCK
  cat > "${root}/bin/curl" <<'MOCK'
#!/usr/bin/env bash
[[ "${MOCK_CURL_FAIL:-0}" != "1" ]]
MOCK
  chmod +x "${root}/bin/"*

  jq -n '{schema:"flowform.rehearsal-state/1", vmids:[210,220,230], status:"created"}' \
    > "${root}/state/state.json"
  jq -n '{schema:"flowform.proxmox-image-manifest/1", image_contract_version:1}' \
    > "${root}/state/image-manifest.json"
  : > "${root}/artifacts/rehearsal-images.tar"
  jq -n '{schema:"flowform.rehearsal-artifact-manifest/1", image_contract_version:1,
    release:"0123456789abcdef0123456789abcdef01234567",
    archive:{file:"rehearsal-images.tar",sha256:"unused"},
    images:{backend:"flowform-backend:0123456789abcdef0123456789abcdef01234567"}}' \
    > "${root}/artifacts/manifest.json"
  (
    cd "${root}/artifacts"
    sha256sum rehearsal-images.tar manifest.json > SHA256SUMS
  )
  : > "${root}/commands.log"
  printf '%s\n' "${root}"
}

run_activation() {
  local root="$1"
  shift
  env \
    PATH="${root}/bin:${PATH}" \
    MOCK_LOG="${root}/commands.log" \
    MOCK_QM_STATE="${root}/qm-state" \
    FLOWFORM_TEST_MODE=1 \
    FLOWFORM_REHEARSAL_TIMEOUT_SECONDS=0 \
    FLOWFORM_REHEARSAL_STATE_DIR="${root}/state" \
    "$@" \
    "${repo_root}/infra/environments/rehearsal/activate.sh" \
    --artifact-manifest "${root}/artifacts/manifest.json"
}

corrupt_root="$(make_case corrupt-bundle)"
printf 'corrupt\n' >> "${corrupt_root}/artifacts/rehearsal-images.tar"
if run_activation "${corrupt_root}" >"${corrupt_root}/output" 2>&1; then
  echo 'corrupt artifact bundle was accepted' >&2
  exit 1
fi
grep -q 'artifact checksum verification failed' "${corrupt_root}/output"
! grep -q '^qm start 220$' "${corrupt_root}/commands.log"

seed_root="$(make_case seed-failure)"
if run_activation "${seed_root}" MOCK_SSH_FAIL_PATTERN=seed-localstack.sh >"${seed_root}/output" 2>&1; then
  echo 'LocalStack seed failure was ignored' >&2
  exit 1
fi
grep -q 'seed-localstack.sh' "${seed_root}/commands.log"
! grep -q '^qm start 220$' "${seed_root}/commands.log"
jq -e '.status == "created"' "${seed_root}/state/state.json" >/dev/null

health_root="$(make_case registry-health-failure)"
if run_activation "${health_root}" MOCK_CURL_FAIL=1 >"${health_root}/output" 2>&1; then
  echo 'registry health failure was ignored' >&2
  exit 1
fi
grep -q 'registry timeout' "${health_root}/output"
! grep -q '^qm start 220$' "${health_root}/commands.log"

printf 'activation failure contracts OK\n'
