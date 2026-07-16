#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../../.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT
mkdir -p "${tmp}/bin" "${tmp}/state/ssh" "${tmp}/artifacts" "${tmp}/qm-state"
log="${tmp}/commands.log"
printf 'test-only-private-key\n' > "${tmp}/state/ssh/id_ed25519"
chmod 0600 "${tmp}/state/ssh/id_ed25519"

cat > "${tmp}/bin/qm" <<'MOCK'
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
cat > "${tmp}/bin/ssh" <<'MOCK'
#!/usr/bin/env bash
printf 'ssh %s\n' "$*" >> "${MOCK_LOG}"
exit 0
MOCK
cat > "${tmp}/bin/scp" <<'MOCK'
#!/usr/bin/env bash
printf 'scp %s\n' "$*" >> "${MOCK_LOG}"
exit 0
MOCK
cat > "${tmp}/bin/ssh-keyscan" <<'MOCK'
#!/usr/bin/env bash
printf 'host ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITestOnlyKey\n'
MOCK
cat > "${tmp}/bin/curl" <<'MOCK'
#!/usr/bin/env bash
exit 0
MOCK
chmod +x "${tmp}/bin/"*

jq -n '{schema:"flowform.rehearsal-state/1", vmids:[210,220,230], status:"created"}' > "${tmp}/state/state.json"
jq -n '{schema:"flowform.proxmox-image-manifest/1", image_contract_version:1}' > "${tmp}/state/image-manifest.json"
touch "${tmp}/artifacts/rehearsal-images.tar"
jq -n '{schema:"flowform.rehearsal-artifact-manifest/1", image_contract_version:1,
  release:"0123456789abcdef0123456789abcdef01234567",
  archive:{file:"rehearsal-images.tar",sha256:"unused"},
  images:{backend:"flowform-backend:0123456789abcdef0123456789abcdef01234567"}}' \
  > "${tmp}/artifacts/manifest.json"
(
  cd "${tmp}/artifacts"
  sha256sum rehearsal-images.tar manifest.json > SHA256SUMS
)

PATH="${tmp}/bin:${PATH}" MOCK_LOG="${log}" MOCK_QM_STATE="${tmp}/qm-state" \
FLOWFORM_TEST_MODE=1 FLOWFORM_REHEARSAL_STATE_DIR="${tmp}/state" \
  "${repo_root}/infra/environments/rehearsal/activate.sh" \
  --artifact-manifest "${tmp}/artifacts/manifest.json"

proxy_line="$(grep -n '^qm start 210$' "${log}" | cut -d: -f1)"
fixtures_line="$(grep -n '^qm start 230$' "${log}" | cut -d: -f1)"
seed_line="$(grep -n 'seed-localstack.sh' "${log}" | cut -d: -f1)"
app_line="$(grep -n '^qm start 220$' "${log}" | cut -d: -f1)"
[[ "${proxy_line}" -lt "${fixtures_line}" && "${fixtures_line}" -lt "${seed_line}" && "${seed_line}" -lt "${app_line}" ]]
jq -e '.status == "active"' "${tmp}/state/state.json" >/dev/null
printf 'activation order OK\n'
