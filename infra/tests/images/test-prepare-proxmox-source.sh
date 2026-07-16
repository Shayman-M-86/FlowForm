#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
script="${repo_root}/images/proxmox/provisioning/01-prepare-proxmox-source.sh"
example_env="${repo_root}/images/proxmox/.env.example"
tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT

fail() {
  printf '[test-prepare-proxmox-source] FAIL: %s\n' "$*" >&2
  exit 1
}

assert_contains() {
  local file="$1"
  local expected="$2"
  grep -Fq -- "${expected}" "${file}" \
    || fail "expected '${expected}' in ${file}"
}

"${script}" --help >"${tmp}/help.out"
assert_contains "${tmp}/help.out" 'The command is non-mutating by default.'

if "${script}" --env-file "${tmp}/missing.env" >"${tmp}/missing.out" 2>&1; then
  fail 'missing environment file unexpectedly succeeded'
fi
assert_contains "${tmp}/missing.out" 'environment file not found'

cp "${example_env}" "${tmp}/valid.env"
sed -i 's/^PROXMOX_SSH_TARGET=.*/PROXMOX_SSH_TARGET=root@fake-pve/' "${tmp}/valid.env"
sed -i "s|^PROXMOX_SSH_IDENTITY_FILE=.*|PROXMOX_SSH_IDENTITY_FILE=${tmp}/fake-id_rsa|" "${tmp}/valid.env"
touch "${tmp}/fake-id_rsa"

cp "${tmp}/valid.env" "${tmp}/invalid.env"
sed -i 's/^PROXMOX_SOURCE_VMID=.*/PROXMOX_SOURCE_VMID=99/' "${tmp}/invalid.env"
if "${script}" --env-file "${tmp}/invalid.env" >"${tmp}/invalid.out" 2>&1; then
  fail 'invalid VMID unexpectedly succeeded'
fi
assert_contains "${tmp}/invalid.out" 'PROXMOX_SOURCE_VMID must be between 100 and 999999999'

fake_bin="${tmp}/bin"
mkdir -p "${fake_bin}"
export FAKE_COMMAND_LOG="${tmp}/commands.log"
: >"${FAKE_COMMAND_LOG}"

cat >"${fake_bin}/ssh" <<'FAKE_SSH'
#!/usr/bin/env bash
set -Eeuo pipefail
printf 'ssh %s\n' "$*" >>"${FAKE_COMMAND_LOG}"
args=("$@")
for (( index=0; index<${#args[@]}; index++ )); do
  if [[ "${args[index]}" == 'bash' ]]; then
    exec "${args[@]:index}"
  fi
done
exit 1
FAKE_SSH

cat >"${fake_bin}/qm" <<'FAKE_QM'
#!/usr/bin/env bash
set -Eeuo pipefail
printf 'qm %s\n' "$*" >>"${FAKE_COMMAND_LOG}"
case "${1:-}" in
  status)
    [[ -n "${FAKE_VM_CONFIG:-}" && -f "${FAKE_VM_CONFIG}" ]] || exit 1
    status="$(cat "${FAKE_VM_STATUS}")"
    start_count="$(cat "${FAKE_VM_START_COUNT}")"
    polls="$(cat "${FAKE_VM_STATUS_POLLS}")"
    if [[ "${status}" == 'running' && "${start_count}" == '1' && "${polls}" -ge 1 ]]; then
      status='stopped'
      printf '%s\n' "${status}" >"${FAKE_VM_STATUS}"
    fi
    printf '%s\n' "$((polls + 1))" >"${FAKE_VM_STATUS_POLLS}"
    printf 'status: %s\n' "${status}"
    ;;
  list) printf ' VMID NAME STATUS MEM(MB) BOOTDISK(GB) PID\n' ;;
  create)
    shift
    name=''
    description=''
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --name) name="$2"; shift 2 ;;
        --description) description="$2"; shift 2 ;;
        *) shift ;;
      esac
    done
    printf 'name: %s\ndescription: %s\n' "${name}" "${description}" >"${FAKE_VM_CONFIG}"
    printf 'stopped\n' >"${FAKE_VM_STATUS}"
    printf '0\n' >"${FAKE_VM_START_COUNT}"
    printf '0\n' >"${FAKE_VM_STATUS_POLLS}"
    ;;
  importdisk)
    printf 'unused0: ZFS-RAIDZ:vm-8999-disk-0\n' >>"${FAKE_VM_CONFIG}"
    ;;
  config) cat "${FAKE_VM_CONFIG}" ;;
  set)
    if [[ "${3:-}" == '--scsi0' ]]; then
      printf 'scsi0: %s,size=25G\n' "${4}" >>"${FAKE_VM_CONFIG}"
    fi
    ;;
  disk) exit 0 ;;
  start)
    count="$(cat "${FAKE_VM_START_COUNT}")"
    printf '%s\n' "$((count + 1))" >"${FAKE_VM_START_COUNT}"
    printf '0\n' >"${FAKE_VM_STATUS_POLLS}"
    printf 'running\n' >"${FAKE_VM_STATUS}"
    ;;
  template) printf 'template: 1\n' >>"${FAKE_VM_CONFIG}" ;;
  *) exit 0 ;;
esac
FAKE_QM

cat >"${fake_bin}/pvesh" <<'FAKE_PVESH'
#!/usr/bin/env bash
set -Eeuo pipefail
printf 'pvesh %s\n' "$*" >>"${FAKE_COMMAND_LOG}"
printf '{}\n'
FAKE_PVESH

cat >"${fake_bin}/pvesm" <<'FAKE_PVESM'
#!/usr/bin/env bash
set -Eeuo pipefail
printf 'pvesm %s\n' "$*" >>"${FAKE_COMMAND_LOG}"
if [[ "${1:-}" == 'path' ]]; then
  printf '/dev/fake-source-disk\n'
  exit 0
fi
printf 'Name Type Status Total Used Available %%\n'
printf 'ZFS-RAIDZ zfspool active 1 0 1 0%%\n'
printf 'local dir active 1 0 1 0%%\n'
FAKE_PVESM

cat >"${fake_bin}/virt-customize" <<'FAKE_VIRT_CUSTOMIZE'
#!/usr/bin/env bash
set -Eeuo pipefail
printf 'virt-customize %s\n' "$*" >>"${FAKE_COMMAND_LOG}"
FAKE_VIRT_CUSTOMIZE

cat >"${fake_bin}/ip" <<'FAKE_IP'
#!/usr/bin/env bash
set -Eeuo pipefail
printf 'ip %s\n' "$*" >>"${FAKE_COMMAND_LOG}"
FAKE_IP

cat >"${fake_bin}/curl" <<'FAKE_CURL'
#!/usr/bin/env bash
set -Eeuo pipefail
printf 'curl %s\n' "$*" >>"${FAKE_COMMAND_LOG}"
output=''
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output) output="$2"; shift 2 ;;
    *) shift ;;
  esac
done
if [[ -n "${output}" ]]; then
  printf 'fake-image' >"${output}"
fi
FAKE_CURL

chmod +x "${fake_bin}"/*

PATH="${fake_bin}:${PATH}" PROXMOX_SSH_BIN="${fake_bin}/ssh" \
  "${script}" --env-file "${tmp}/valid.env" >"${tmp}/preflight.out"

assert_contains "${tmp}/preflight.out" 'preflight OK'
assert_contains "${tmp}/preflight.out" 'preflight complete; no Proxmox resources were changed'

if grep -Eq '^(qm (create|importdisk|set|disk|start|guest|shutdown|template|destroy|stop)|pvesm set)' \
  "${FAKE_COMMAND_LOG}"; then
  fail 'preflight invoked a mutating Proxmox command'
fi

cp "${tmp}/valid.env" "${tmp}/apply.env"
mkdir -p "${tmp}/remote"
sed -i "s|^PROXMOX_SNIPPET_DIR=.*|PROXMOX_SNIPPET_DIR=${tmp}/remote/snippets|" "${tmp}/apply.env"
sed -i "s|^PROXMOX_IMAGE_CACHE_DIR=.*|PROXMOX_IMAGE_CACHE_DIR=${tmp}/remote/images|" "${tmp}/apply.env"
fake_checksum="$(printf 'fake-image' | sha256sum | awk '{ print $1 }')"
sed -i "s/^AL2023_IMAGE_SHA256=.*/AL2023_IMAGE_SHA256=${fake_checksum}/" "${tmp}/apply.env"

export FAKE_VM_CONFIG="${tmp}/vm.config"
export FAKE_VM_STATUS="${tmp}/vm.status"
export FAKE_VM_START_COUNT="${tmp}/vm.start-count"
export FAKE_VM_STATUS_POLLS="${tmp}/vm.status-polls"
: >"${FAKE_COMMAND_LOG}"

PATH="${fake_bin}:${PATH}" PROXMOX_SSH_BIN="${fake_bin}/ssh" \
  "${script}" --env-file "${tmp}/apply.env" --apply >"${tmp}/apply.out"

assert_contains "${tmp}/apply.out" 'source template ready: 8999 (amazon-linux-2023-kvm-base)'
assert_contains "${tmp}/apply.out" 'source-template preparation complete'
assert_contains "${FAKE_VM_CONFIG}" 'template: 1'
assert_contains "${FAKE_COMMAND_LOG}" 'qm importdisk 8999'
assert_contains "${FAKE_COMMAND_LOG}" '--agent enabled=0'
assert_contains "${FAKE_COMMAND_LOG}" '--cpu x86-64-v2-AES'
assert_contains "${FAKE_COMMAND_LOG}" 'qm disk resize 8999 scsi0 32G'
assert_contains "${FAKE_COMMAND_LOG}" 'virt-customize -a /dev/fake-source-disk'
assert_contains "${FAKE_COMMAND_LOG}" '--run-command cloud-init clean --logs'
assert_contains "${FAKE_COMMAND_LOG}" 'qm template 8999'

printf 'prepare-proxmox-source tests OK\n'
