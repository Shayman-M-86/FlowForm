#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../../.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT
mkdir -p "${tmp}/bin" "${tmp}/qm-state" "${tmp}/snippets" "${tmp}/state"
log="${tmp}/commands.log"

cat > "${tmp}/bin/qm" <<'MOCK'
#!/usr/bin/env bash
set -Eeuo pipefail
printf 'qm %s\n' "$*" >> "${MOCK_LOG}"
case "$1" in
  status)
    [[ "$2" == "9100" || -f "${MOCK_QM_STATE}/$2" ]]
    ;;
  config)
    if [[ "$2" == "9100" ]]; then
      printf 'template: 1\nname: flowform-golden-test-9100\n'
    else
      printf 'name: flowform-rehearsal-test\n'
    fi
    ;;
  clone)
    touch "${MOCK_QM_STATE}/$3"
    ;;
  set|stop|destroy|list) ;;
  *) exit 1 ;;
esac
MOCK
cat > "${tmp}/bin/pvesm" <<'MOCK'
#!/usr/bin/env bash
printf 'local snippets\n'
MOCK
cat > "${tmp}/bin/ip" <<'MOCK'
#!/usr/bin/env bash
exit 0
MOCK
chmod +x "${tmp}/bin/"*

jq -n '{schema:"flowform.proxmox-image-manifest/1", image_contract_version:1,
  vmid:9100, name:"flowform-golden-test-9100", smoke_verified:true}' > "${tmp}/manifest.json"

PATH="${tmp}/bin:${PATH}" \
MOCK_LOG="${log}" MOCK_QM_STATE="${tmp}/qm-state" \
FLOWFORM_TEST_MODE=1 FLOWFORM_REHEARSAL_STATE_DIR="${tmp}/state" \
PROXMOX_SNIPPET_DIR="${tmp}/snippets" REPO_ROOT="${repo_root}" \
  "${repo_root}/infra/platforms/proxmox/create-vms.sh" \
  --image-manifest "${tmp}/manifest.json" --with-dev

! grep -q '^qm start ' "${log}" || { echo 'create-vms started a VM' >&2; exit 1; }
[[ "$(grep -c '^qm clone 9100 ' "${log}")" == "4" ]]
for vmid in 210 220 230 240; do
  grep -q "^qm set ${vmid} .*--cicustom" "${log}"
done
jq -e '.status == "created" and .vmids == [210,220,230,240]' "${tmp}/state/state.json" >/dev/null
printf 'create-vms contract OK\n'
