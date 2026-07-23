#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_LIB_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_ROOT="$(cd -- "${SCRIPT_LIB_DIR}/../.." && pwd)"
PACKER_DIR="${IMAGE_ROOT}/packer"

# The dispatcher provides structured versions. Keep small fallbacks so the
# validation suite can source this focused library directly.
declare -F die >/dev/null || die() { printf '[flowform-packer] ERROR: %s\n' "$*" >&2; exit 1; }
declare -F log >/dev/null || log() { printf '[flowform-packer] %s\n' "$*"; }
declare -F success >/dev/null || success() { log "$*"; }
declare -F require_command >/dev/null || require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

require_vars_file() {
  local vars_file="$1"
  local example_name="$2"
  [[ -f "${vars_file}" ]] \
    || die "missing ${vars_file}; copy ${PACKER_DIR}/variables/${example_name} and fill it in"
}

assert_proxmox_build_ip_available() {
  local vars_file="$1"
  local build_ip_cidr build_ip
  build_ip_cidr="$(awk -F'"' \
    '$1 ~ /^[[:space:]]*proxmox_build_ip_cidr[[:space:]]*=[[:space:]]*$/ { print $2; exit }' \
    "${vars_file}")"
  [[ "${build_ip_cidr}" == */* ]] \
    || die "proxmox_build_ip_cidr is missing or invalid in ${vars_file}"
  build_ip="${build_ip_cidr%%/*}"
  if command -v ping >/dev/null 2>&1 && ping -c 1 -W 1 "${build_ip}" >/dev/null 2>&1; then
    die "dedicated Packer address ${build_ip} is already responding"
  fi
}

run_packer_build() (
  local build_file="$1"
  local only_target="$2"
  local vars_file="$3"
  local project_dir
  local -a validate_args

  require_command packer
  [[ -f "${build_file}" ]] || die "Packer build file not found: ${build_file}"
  [[ -f "${vars_file}" ]] || die "Packer variable file not found: ${vars_file}"
  build_file="$(realpath -- "${build_file}")"
  vars_file="$(realpath -- "${vars_file}")"

  project_dir="$(mktemp -d)"
  trap 'rm -rf "${project_dir}"' EXIT

  ln -s "${PACKER_DIR}/plugins.pkr.hcl" "${project_dir}/plugins.pkr.hcl"
  ln -s "${PACKER_DIR}/locals.pkr.hcl" "${project_dir}/locals.pkr.hcl"
  for config_file in "${PACKER_DIR}"/sources/*.pkr.hcl; do
    ln -s "${config_file}" "${project_dir}/source-$(basename -- "${config_file}")"
  done
  for config_file in "${PACKER_DIR}"/variables/*.pkr.hcl; do
    ln -s "${config_file}" "${project_dir}/variable-$(basename -- "${config_file}")"
  done
  ln -s "${build_file}" "${project_dir}/build-$(basename -- "${build_file}")"

  log "initializing Packer project for $(basename -- "${build_file}")"
  packer init "${project_dir}"
  log "validating Packer target ${only_target}"
  validate_args=(
    -only="${only_target}"
    -var "image_root=${IMAGE_ROOT}"
    -var-file="${vars_file}"
  )
  if [[ "${PACKER_SYNTAX_ONLY:-0}" == "1" ]]; then
    validate_args=(-syntax-only "${validate_args[@]}")
  fi
  packer validate "${validate_args[@]}" "${project_dir}"

  if [[ "${PACKER_VALIDATE_ONLY:-0}" == "1" ]]; then
    success "Packer validation complete for ${only_target}"
    exit 0
  fi

  log "building Packer target ${only_target}"
  packer build \
    -only="${only_target}" \
    -var "image_root=${IMAGE_ROOT}" \
    -var-file="${vars_file}" \
    "${project_dir}"
)
