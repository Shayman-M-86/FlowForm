#!/usr/bin/env bash
set -Eeuo pipefail

# Build the Proxmox template after the reusable source template has been prepared.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PACKER_DIR="$(cd -- "${SCRIPT_DIR}/../../packer" && pwd)"
VARS_FILE="${PACKER_DIR}/proxmox.auto.pkrvars.hcl"

[[ -f "${VARS_FILE}" ]] || {
  printf 'Missing %s; copy variables/proxmox.auto.pkrvars.hcl.example and fill it in.\n' "${VARS_FILE}" >&2
  exit 1
}

build_ip_cidr="$(awk -F'"' \
  '$1 ~ /^[[:space:]]*proxmox_build_ip_cidr[[:space:]]*=[[:space:]]*$/ { print $2; exit }' \
  "${VARS_FILE}")"
[[ "${build_ip_cidr}" == */* ]] || {
  printf 'proxmox_build_ip_cidr is missing or invalid in %s\n' "${VARS_FILE}" >&2
  exit 1
}
build_ip="${build_ip_cidr%%/*}"

if command -v ping >/dev/null 2>&1 && ping -c 1 -W 1 "${build_ip}" >/dev/null 2>&1; then
  printf 'Refusing to build: dedicated Packer address %s is already responding.\n' "${build_ip}" >&2
  exit 1
fi

cd "${PACKER_DIR}"
packer init .
packer validate -syntax-only .
packer build -only='flowform-golden.proxmox-clone.amazon_linux_2023' .
