#!/usr/bin/env bash
# `rehearsal build` — converge the Proxmox rehearsal in dependency order:
#
#   [destroy] -> apply -> sync secrets -> proxy -> prepare app relay
#             -> [database || prepare images] -> publish images -> app -> verify
#
# The ordering is load-bearing. Secret sync requires VM 230. Database bootstrap
# and image publication require Squid on the proxy. Image publication relays
# through the app VM's Docker daemon, and the app stack can become healthy only
# after both images are in the isolated registry.
#
# Usage:
#   rehearsal build
#   rehearsal build --fresh
#   rehearsal build --fresh -- -auto-approve
#
# `--fresh` removes Terraform-managed VMs/snippets, not the root-only secret
# bundle under /var/lib/flowform on the PVE host. The command fingerprints an
# existing bundle across destroy/apply/sync and fails if it unexpectedly changes.

BUILD_CHILD_PIDS=()
BUILD_WORK_DIR=""
BUILD_STARTED_AT=""
BUILD_CURRENT_STEP="startup"
BUILD_SUMMARY_EMITTED=0

_cmd_build_cleanup_resources() {
  local pid
  for pid in "${BUILD_CHILD_PIDS[@]}"; do
    kill "${pid}" >/dev/null 2>&1 || true
  done
  for pid in "${BUILD_CHILD_PIDS[@]}"; do
    wait "${pid}" >/dev/null 2>&1 || true
  done
  BUILD_CHILD_PIDS=()
  if [[ -n "${BUILD_WORK_DIR}" && -d "${BUILD_WORK_DIR}" ]]; then
    rm -r -- "${BUILD_WORK_DIR}"
    BUILD_WORK_DIR=""
  fi
  rehearsal_bridge_down
}

_cmd_build_cleanup_exit() {
  local status=$?
  trap - EXIT INT TERM HUP
  _cmd_build_cleanup_resources
  if (( status != 0 && BUILD_SUMMARY_EMITTED == 0 )); then
    local elapsed=0
    [[ -z "${BUILD_STARTED_AT}" ]] || elapsed=$(( $(date +%s) - BUILD_STARTED_AT ))
    phase "build summary"
    error "RESULT: FAIL — stopped during ${BUILD_CURRENT_STEP} after ${elapsed}s"
    log "next: review the last ERROR above, correct it, then rerun the same rehearsal build command"
    BUILD_SUMMARY_EMITTED=1
  fi
  exit "${status}"
}

_cmd_build_cleanup_signal() {
  trap - EXIT INT TERM HUP
  _cmd_build_cleanup_resources
  phase "build summary"
  warn "RESULT: INTERRUPTED — stopped during ${BUILD_CURRENT_STEP}"
  BUILD_SUMMARY_EMITTED=1
  exit 130
}

cmd_build_main() {
  local here repo_root registry_dir push_script alloy_script dispatcher
  here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
  dispatcher="${here}/rehearsal"
  repo_root="$(cd -- "${here}/../../../.." && pwd)"
  registry_dir="${repo_root}/infra/containers/strategies/rehearsal/services/registry"
  push_script="${registry_dir}/build-and-push-backend.sh"
  alloy_script="${registry_dir}/mirror-alloy-image.sh"
  BUILD_STARTED_AT="$(date +%s)"
  trap _cmd_build_cleanup_exit EXIT
  trap _cmd_build_cleanup_signal INT TERM HUP

  local fresh=0 apply_args=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --fresh) fresh=1; shift ;;
      --) shift; apply_args+=("$@"); break ;;
      -h|--help)
        sed -n '/^# Usage:/,/^[^#]/p' "${BASH_SOURCE[0]}" | grep '^#' | sed 's/^# \{0,1\}//'
        return 0
        ;;
      *) die "unknown build argument: $1 (put Terraform arguments after '--')" ;;
    esac
  done

  rehearsal_preflight
  # Resolve every external secret and check PVE tooling BEFORE an optional
  # Terraform destroy. `sync` repeats this after apply because credentials can
  # expire, but a missing input must never be discovered only after teardown.
  # shellcheck source=rehearsal-secrets.sh
  source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/rehearsal-secrets.sh"
  secrets_preflight_build_inputs
  [[ -x "${dispatcher}" ]]   || die "dispatcher not executable: ${dispatcher}"
  [[ -x "${push_script}" ]]  || die "backend publisher not executable: ${push_script}"
  [[ -x "${alloy_script}" ]] || die "Alloy mirror not executable: ${alloy_script}"
  # shellcheck source=rehearsal-terraform.sh
  source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/rehearsal-terraform.sh"

  local bundle_dir bundle_before="" bundle_after=""
  bundle_dir="${REHEARSAL_SECRET_BUNDLE_DIR:-/var/lib/flowform/rehearsal-secrets/${FLOWFORM_SCOPE:-nonprod}}"
  bundle_fingerprint() {
    pve_ssh "BUNDLE_DIR='${bundle_dir}' bash -s" <<'REMOTE'
set -Eeuo pipefail
if [[ -d "${BUNDLE_DIR}" ]]; then
  cd "${BUNDLE_DIR}"
  for file in app_secret_key db_core_app_password db_response_app_password linkage_history.json; do
    [[ -f "${file}" ]] || exit 0
  done
  sha256sum app_secret_key db_core_app_password db_response_app_password linkage_history.json \
    | sha256sum | awk '{print $1}'
fi
REMOTE
  }

  if (( fresh == 1 )); then
    bundle_before="$(bundle_fingerprint)"
    BUILD_CURRENT_STEP="step 0/8 (Terraform destroy)"
    phase "step 0/8: Terraform destroy (--fresh) — removing VMs, registry, and seeded state"
    rehearsal_terraform destroy "${apply_args[@]}"
  fi

  BUILD_CURRENT_STEP="step 1/8 (Terraform apply)"
  phase "step 1/8: Terraform apply — clone/converge the rehearsal topology"
  rehearsal_terraform apply "${apply_args[@]}"

  BUILD_CURRENT_STEP="step 2/8 (secret synchronisation)"
  phase "step 2/8: synchronise the persistent secret bundle into LocalStack"
  "${dispatcher}" sync

  if (( fresh == 1 )) && [[ -n "${bundle_before}" ]]; then
    bundle_after="$(bundle_fingerprint)"
    [[ "${bundle_after}" == "${bundle_before}" ]] \
      || die "persistent secret bundle changed across --fresh; refusing to continue"
    log "persistent secret bundle survived --fresh unchanged"
  fi

  rehearsal_bridge_up
  BUILD_WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/flowform-rehearsal-build.XXXXXX")" \
    || die "could not create build work directory"
  chmod 0700 "${BUILD_WORK_DIR}"

  BUILD_CURRENT_STEP="step 3/8 (proxy convergence)"
  phase "step 3/8: converge proxy so Squid is available to isolated guests"
  rehearsal_converge proxy || die "proxy convergence failed"

  local legacy_env=(
    "PROXMOX_SSH_TARGET=${PVE_USER}@${PVE_HOST}"
    "PROXMOX_SSH_KEY=${PVE_SSH_KEY}"
    "PROXMOX_PRIVATE_BRIDGE=${BRIDGE}"
    "PROXMOX_TEMP_BRIDGE_CIDR=${BRIDGE_CIDR}"
    "PUSH_RELAY_SSH_TARGET=${GUEST_USER}@$(rehearsal_ip app)"
    "PUSH_RELAY_KNOWN_HOSTS_FILE=${BUILD_WORK_DIR}/guest-known-hosts"
  )

  BUILD_CURRENT_STEP="step 4/8 (image-relay preparation)"
  phase "step 4/8: prepare app VM 220 as the isolated image relay"
  rehearsal_wait_for_guest app \
    "${REHEARSAL_GUEST_MAX_ATTEMPTS:-60}" \
    "${REHEARSAL_GUEST_RETRY_DELAY_SECONDS:-2}" \
    || die "app VM is unreachable for image-relay preparation"
  guest_ssh "$(rehearsal_ip app)" \
    "sudo env BOOTSTRAP_PREPARE_ONLY=1 $(rehearsal_bootstrap_launcher app)" \
    || die "app image-relay preparation failed"

  BUILD_CURRENT_STEP="step 5/8 (parallel database and image preparation)"
  phase "step 5/8: concurrently converge PostgreSQL and prepare backend + Alloy images"
  (rehearsal_converge db) >"${BUILD_WORK_DIR}/database.log" 2>&1 &
  local db_pid=$!
  BUILD_CHILD_PIDS+=("${db_pid}")
  (env "${legacy_env[@]}" PUBLISH_PREPARE_ONLY=1 "${push_script}") \
    >"${BUILD_WORK_DIR}/backend-prepare.log" 2>&1 &
  local backend_pid=$!
  BUILD_CHILD_PIDS+=("${backend_pid}")
  (env "${legacy_env[@]}" PUBLISH_PREPARE_ONLY=1 "${alloy_script}") \
    >"${BUILD_WORK_DIR}/alloy-prepare.log" 2>&1 &
  local alloy_pid=$!
  BUILD_CHILD_PIDS+=("${alloy_pid}")

  local parallel_status=0 job_status=0
  if wait "${db_pid}"; then job_status=0; else job_status=$?; parallel_status=1; fi
  rehearsal_replay_log "database branch" "${BUILD_WORK_DIR}/database.log"
  ((job_status == 0)) || log "ERROR: database branch exited ${job_status}"
  if wait "${backend_pid}"; then job_status=0; else job_status=$?; parallel_status=1; fi
  rehearsal_replay_log "backend prepare" "${BUILD_WORK_DIR}/backend-prepare.log"
  ((job_status == 0)) || log "ERROR: backend preparation exited ${job_status}"
  if wait "${alloy_pid}"; then job_status=0; else job_status=$?; parallel_status=1; fi
  rehearsal_replay_log "Alloy prepare" "${BUILD_WORK_DIR}/alloy-prepare.log"
  ((job_status == 0)) || log "ERROR: Alloy preparation exited ${job_status}"
  BUILD_CHILD_PIDS=()
  ((parallel_status == 0)) \
    || die "parallel database/image preparation failed; review the named branch output above"

  BUILD_CURRENT_STEP="step 6/8 (image publication)"
  phase "step 6/8: publish required images through one prepared relay"
  env "${legacy_env[@]}" PUBLISH_SKIP_PREPARE=1 "${push_script}"
  env "${legacy_env[@]}" PUBLISH_SKIP_PREPARE=1 PUSH_RELAY_READY=1 "${alloy_script}"

  BUILD_CURRENT_STEP="step 7/8 (application convergence)"
  phase "step 7/8: converge the app after both images and all secrets are present"
  rehearsal_converge app || die "application convergence failed"

  BUILD_CURRENT_STEP="step 8/8 (end-to-end verification)"
  phase "step 8/8: verify the converged rehearsal end to end"
  "${dispatcher}" verify || die "rehearsal verification failed"
  local build_elapsed=$(( $(date +%s) - BUILD_STARTED_AT ))
  phase "build summary"
  success "RESULT: PASS — rehearsal build and verification completed in ${build_elapsed}s"
  log "topology, secrets, proxy, database, images, application, and verification all completed"
  BUILD_SUMMARY_EMITTED=1
}
