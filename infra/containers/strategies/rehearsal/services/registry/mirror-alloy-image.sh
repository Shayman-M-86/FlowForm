#!/usr/bin/env bash
set -Eeuo pipefail

# Mirror the public grafana/alloy image into the rehearsal's private registry.
#
# WHY: the app box (10.10.10.20) is offline — its only egress is Squid, which
# admits registry.localstack.test (fake ECR) and a few AWS/Auth0 names, NOT
# Docker Hub. So its Alloy image cannot be pulled from grafana/alloy at boot; it
# must live in the fake registry, exactly like the backend image. The app box's
# ALLOY_IMAGE is set to registry.localstack.test/grafana/alloy:<tag>.
#
# This is the observability sibling of build-and-push-backend.sh and reuses the
# same relay: the registry is reachable only from the app VM through Squid, so we
# pull+retag on this (internet-connected) dev box, stream the image to the app VM
# over SSH, and push from there through the app daemon's proxy drop-in.
#
# WHERE THIS RUNS: a host with Docker + internet + SSH access to the Proxmox host
# (the dev box). Idempotent: an unchanged image is a no-op push.
#
# Usage:
#   mirror-alloy-image.sh                       # mirrors the default tag
#   ALLOY_VERSION=v1.5.1 mirror-alloy-image.sh   # pin a tag

REGISTRY_HOST="${REGISTRY_HOST:-registry.localstack.test}"   # no port ⇒ 443/HTTPS
ALLOY_VERSION="${ALLOY_VERSION:-v1.5.1}"
SOURCE_IMAGE="${SOURCE_IMAGE:-grafana/alloy:${ALLOY_VERSION}}"
# Must match ALLOY_IMAGE in the app cloud-init (app.yaml.tftpl).
DEST_IMAGE="${DEST_IMAGE:-${REGISTRY_HOST}/grafana/alloy:${ALLOY_VERSION}}"

PROXMOX_SSH_TARGET="${PROXMOX_SSH_TARGET:-root@192.168.68.88}"
PROXMOX_SSH_KEY="${PROXMOX_SSH_KEY:-${HOME}/.ssh/proxmox_codex}"
PROXMOX_PRIVATE_BRIDGE="${PROXMOX_PRIVATE_BRIDGE:-vmbr10}"
PROXMOX_TEMP_BRIDGE_CIDR="${PROXMOX_TEMP_BRIDGE_CIDR:-10.10.10.1/24}"
PUSH_RELAY_SSH_TARGET="${PUSH_RELAY_SSH_TARGET:-ec2-user@10.10.10.20}"
SQUID_PROXY_URL="${SQUID_PROXY_URL:-http://10.10.10.10:3128}"
PUBLISH_PREPARE_ONLY="${PUBLISH_PREPARE_ONLY:-0}"
PUBLISH_SKIP_PREPARE="${PUBLISH_SKIP_PREPARE:-0}"
PUSH_RELAY_READY="${PUSH_RELAY_READY:-0}"
PUSH_RELAY_KNOWN_HOSTS_FILE="${PUSH_RELAY_KNOWN_HOSTS_FILE:-/dev/null}"

ADDED_BRIDGE_ADDRESS=0

publisher_log() { # fd level message...
  local fd="$1" level="$2" colour="" reset=""; shift 2
  if [[ -z "${NO_COLOR:-}" && -t "${fd}" && "${REHEARSAL_COLOR:-auto}" != never ]]; then
    reset=$'\033[0m'
    [[ "${level}" == ERROR ]] && colour=$'\033[1;31m' || colour=$'\033[0;36m'
  fi
  printf '%s | %b%-7s%b | %-20s | %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
    "${colour}" "${level}" "${reset}" mirror-alloy "$*" >&"${fd}"
}
log() { publisher_log 1 INFO "$*"; }
die() { publisher_log 2 ERROR "$*"; exit 1; }

# Retry a command with fixed-delay backoff — see build-and-push-backend.sh for
# the rationale (right after `terraform apply` the relay SSH and the TLS shim on
# VM 230 may still be seconds from ready; a fail-fast preflight turns that
# ordinary startup race into a spurious failure). Returns immediately on the
# first success; on exhaustion returns the last failure so callers fail closed.
#   retry_with_backoff "<description>" <attempts> <delay_seconds> cmd arg...
retry_with_backoff() {
  local description="$1" attempts="$2" delay_seconds="$3"
  shift 3
  local attempt
  for ((attempt = 1; attempt <= attempts; attempt++)); do
    if "$@"; then
      return 0
    fi
    if ((attempt < attempts)); then
      if ((attempt == 1 || attempt % 5 == 0)); then
        log "${description} not ready (${attempt}/${attempts}); retrying in ${delay_seconds}s"
      fi
      sleep "${delay_seconds}"
    fi
  done
  return 1
}

RELAY_MAX_ATTEMPTS="${PUSH_RELAY_MAX_ATTEMPTS:-60}"
RELAY_RETRY_DELAY_SECONDS="${PUSH_RELAY_RETRY_DELAY_SECONDS:-2}"
PREFLIGHT_MAX_ATTEMPTS="${PUSH_PREFLIGHT_MAX_ATTEMPTS:-60}"
PREFLIGHT_RETRY_DELAY_SECONDS="${PUSH_PREFLIGHT_RETRY_DELAY_SECONDS:-2}"

cleanup() {
  local status=$?
  trap - EXIT INT TERM HUP
  if (( ADDED_BRIDGE_ADDRESS == 1 )); then
    log "removing temporary ${PROXMOX_TEMP_BRIDGE_CIDR} address from ${PROXMOX_PRIVATE_BRIDGE}"
    ssh "${SSH_OPTIONS[@]}" "${PROXMOX_SSH_TARGET}" \
      "ip address del '${PROXMOX_TEMP_BRIDGE_CIDR}' dev '${PROXMOX_PRIVATE_BRIDGE}'" \
      >/dev/null 2>&1 || log "WARNING: could not remove the temporary bridge address; remove it manually"
  fi
  exit "${status}"
}
trap cleanup EXIT

command -v docker >/dev/null 2>&1 || die "docker not found on this box"
command -v ssh >/dev/null 2>&1 || die "ssh not found on this box"
[[ -f "${PROXMOX_SSH_KEY}" ]] || die "Proxmox SSH key not found at ${PROXMOX_SSH_KEY}"
[[ "${DEST_IMAGE}" =~ ^[a-zA-Z0-9._:/-]+$ ]] || die "invalid image destination ${DEST_IMAGE}"
for flag in PUBLISH_PREPARE_ONLY PUBLISH_SKIP_PREPARE PUSH_RELAY_READY; do
  [[ "${!flag}" == "0" || "${!flag}" == "1" ]] || die "${flag} must be 0 or 1"
done
[[ "${PUBLISH_PREPARE_ONLY}" != "1" || "${PUBLISH_SKIP_PREPARE}" != "1" ]] \
  || die "PUBLISH_PREPARE_ONLY and PUBLISH_SKIP_PREPARE are mutually exclusive"

SSH_OPTIONS=(
  -i "${PROXMOX_SSH_KEY}"
  -o BatchMode=yes
  -o ConnectTimeout=10
  -o ServerAliveInterval=15
  -o ServerAliveCountMax=3
)

relay_ssh() {
  ssh "${SSH_OPTIONS[@]}" \
    -o "UserKnownHostsFile=${PUSH_RELAY_KNOWN_HOSTS_FILE}" \
    -o StrictHostKeyChecking=accept-new \
    -o "ProxyCommand=ssh -i ${PROXMOX_SSH_KEY} -o BatchMode=yes -W %h:%p ${PROXMOX_SSH_TARGET}" \
    "${PUSH_RELAY_SSH_TARGET}" "$@"
}

prepare_push_relay() {
  log "preparing temporary image relay through ${PROXMOX_SSH_TARGET}"
  ssh "${SSH_OPTIONS[@]}" "${PROXMOX_SSH_TARGET}" "ip link show '${PROXMOX_PRIVATE_BRIDGE}'" >/dev/null \
    || die "cannot access ${PROXMOX_PRIVATE_BRIDGE} on ${PROXMOX_SSH_TARGET}"

  if ssh "${SSH_OPTIONS[@]}" "${PROXMOX_SSH_TARGET}" \
    "ip -4 -o address show dev '${PROXMOX_PRIVATE_BRIDGE}' | awk '{print \$4}' | grep -Fqx '${PROXMOX_TEMP_BRIDGE_CIDR}'"; then
    log "${PROXMOX_TEMP_BRIDGE_CIDR} is already present; leaving it untouched during cleanup"
  else
    ssh "${SSH_OPTIONS[@]}" "${PROXMOX_SSH_TARGET}" \
      "ip address add '${PROXMOX_TEMP_BRIDGE_CIDR}' dev '${PROXMOX_PRIVATE_BRIDGE}'" \
      || die "could not add the temporary bridge address"
    ADDED_BRIDGE_ADDRESS=1
  fi

  # Reachability: the temporary bridge address was just added, so the app VM may
  # not have ARP-resolved it yet — the SSH ProxyCommand's first connect can fail
  # with "No route to host" purely on timing. Retry a no-op relay login until the
  # path settles rather than dying on that race.
  retry_with_backoff "app VM relay SSH (${PUSH_RELAY_SSH_TARGET})" \
    "${RELAY_MAX_ATTEMPTS}" "${RELAY_RETRY_DELAY_SECONDS}" \
    relay_ssh true \
    || die "app VM relay ${PUSH_RELAY_SSH_TARGET} unreachable via ${PROXMOX_SSH_TARGET} after ${RELAY_MAX_ATTEMPTS} attempts"

  # Preflight (retried): right after `terraform apply` the TLS shim / registry on
  # VM 230 are the last services to come healthy, so this path often needs a few
  # seconds — a wait, not a failure.
  retry_with_backoff "registry reachable through Squid" \
    "${PREFLIGHT_MAX_ATTEMPTS}" "${PREFLIGHT_RETRY_DELAY_SECONDS}" \
    relay_ssh \
    "curl -fsS --connect-timeout 3 --max-time 5 --proxy '${SQUID_PROXY_URL}' 'https://${REGISTRY_HOST}/v2/' >/dev/null && sudo docker info >/dev/null" \
    || die "app VM relay ${PUSH_RELAY_SSH_TARGET} cannot reach https://${REGISTRY_HOST} through Squid or Docker is down after ${PREFLIGHT_MAX_ATTEMPTS} attempts"

  log "temporary image relay is ready through ${PUSH_RELAY_SSH_TARGET}"
}

if [[ "${PUBLISH_SKIP_PREPARE}" != "1" ]]; then
  log "pulling ${SOURCE_IMAGE} from Docker Hub"
  docker pull "${SOURCE_IMAGE}"
  log "retagging -> ${DEST_IMAGE}"
  docker tag "${SOURCE_IMAGE}" "${DEST_IMAGE}"
fi

if [[ "${PUBLISH_PREPARE_ONLY}" == "1" ]]; then
  log "Alloy image prepared locally; publication deferred"
  exit 0
fi

[[ "${PUSH_RELAY_READY}" == "1" ]] || prepare_push_relay

local_config_digest="$(docker image inspect --format '{{.Id}}' "${DEST_IMAGE}")"
remote_config_digest="$(relay_ssh \
  "curl -fsS --connect-timeout 3 --max-time 10 --proxy '${SQUID_PROXY_URL}' -H 'Accept: application/vnd.docker.distribution.manifest.v2+json' 'https://${REGISTRY_HOST}/v2/grafana/alloy/manifests/${ALLOY_VERSION}' 2>/dev/null | jq -er '.config.digest // empty'" \
  2>/dev/null || true)"
if [[ -n "${remote_config_digest}" && "${remote_config_digest}" == "${local_config_digest}" ]]; then
  log "registry already has ${DEST_IMAGE} with config digest ${local_config_digest}; skipping stream and push"
  exit 0
fi

log "streaming ${DEST_IMAGE} to the app VM and pushing through Squid"
docker image save "${DEST_IMAGE}" \
  | relay_ssh "sudo docker image load >/dev/null && sudo docker push '${DEST_IMAGE}'"

log "done. Registry catalog:"
relay_ssh \
  "curl -fsS --connect-timeout 3 --max-time 10 --proxy '${SQUID_PROXY_URL}' 'https://${REGISTRY_HOST}/v2/_catalog'" \
  | sed 's/^/  /'
log "app box (220) ALLOY_IMAGE should be: ${DEST_IMAGE}"
