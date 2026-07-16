#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage: smoke-test-template.sh --template-vmid ID [--smoke-vmid ID]

Run on Proxmox VE. Clones a candidate, verifies first-boot identity and required
host tools through QEMU guest agent, then always destroys the smoke VM.
USAGE
}

log() { printf '[smoke-test-template] %s\n' "$*"; }
die() { printf '[smoke-test-template] ERROR: %s\n' "$*" >&2; exit 1; }

template_vmid=""
smoke_vmid=""
timeout="${SMOKE_TIMEOUT_SECONDS:-300}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --template-vmid) template_vmid="${2:-}"; shift 2 ;;
    --smoke-vmid) smoke_vmid="${2:-}"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done
[[ "${template_vmid}" =~ ^[1-9][0-9]{2,8}$ ]] || die "--template-vmid is required"
for command in qm jq base64; do
  command -v "${command}" >/dev/null 2>&1 || die "required command not found: ${command}"
done
smoke_vmid="${smoke_vmid:-$((template_vmid + 100000))}"
qm status "${template_vmid}" >/dev/null 2>&1 || die "template ${template_vmid} not found"
qm status "${smoke_vmid}" >/dev/null 2>&1 && die "smoke VMID ${smoke_vmid} already exists"

cleanup() {
  qm stop "${smoke_vmid}" >/dev/null 2>&1 || true
  qm destroy "${smoke_vmid}" --purge >/dev/null 2>&1 || true
}
trap cleanup EXIT

qm clone "${template_vmid}" "${smoke_vmid}" --name "flowform-image-smoke-${template_vmid}" --full
qm set "${smoke_vmid}" --net0 virtio,bridge=vmbr0 --ipconfig0 ip=dhcp --ciuser flowform
qm start "${smoke_vmid}"

deadline=$((SECONDS + timeout))
until qm guest ping "${smoke_vmid}" >/dev/null 2>&1; do
  (( SECONDS < deadline )) || die "QEMU guest agent did not become ready within ${timeout}s"
  sleep 2
done

result="$(qm guest exec "${smoke_vmid}" -- bash -lc '
  set -Eeuo pipefail
  test -s /etc/machine-id
  compgen -G "/etc/ssh/ssh_host_*_key.pub" >/dev/null
  command -v cloud-init >/dev/null
  command -v docker >/dev/null
  docker compose version >/dev/null
  command -v aws >/dev/null
  systemctl is-enabled qemu-guest-agent >/dev/null
  printf "docker=%s\n" "$(docker --version)"
  printf "compose=%s\n" "$(docker compose version)"
  printf "aws=%s\n" "$(aws --version 2>&1)"
  printf "cloud-init=%s\n" "$(cloud-init --version 2>&1)"
  printf "qemu-guest-agent=%s\n" "$(qemu-ga --version 2>&1 | head -n 1)"
')"
jq -e '.exitcode == 0' <<<"${result}" >/dev/null || die "guest verification failed: ${result}"
tool_report="$(jq -r '.["out-data"] // empty' <<<"${result}")"
[[ -n "${tool_report}" ]] || die "guest verification returned no tool report"
log "candidate ${template_vmid} passed smoke verification"
printf 'FLOWFORM_SMOKE_REPORT_B64=%s\n' "$(printf '%s' "${tool_report}" | base64 -w0)"
