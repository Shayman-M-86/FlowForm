#!/usr/bin/env bash
set -Eeuo pipefail

# Build the FlowForm backend image and push it to the rehearsal's private
# registry, so the offline app box (220) can pull it at bootstrap — mirroring how
# real EC2 pulls BACKEND_IMAGE from ECR and never from the internet.
#
# WHERE THIS RUNS: a host with Docker, internet, the repo checkout, and SSH
# access to the Proxmox host. A dual-homed dev box can push directly. From WSL or
# another LAN workstation, this script temporarily gives the Proxmox host an IP
# on vmbr10 and streams the built image over SSH to the app VM, whose Docker
# daemon can reach the private registry. The address is removed after the push,
# including when the build or push fails.
#
# WHAT IT PROVES / DOESN'T: this is the rehearsal stand-in for the ECR push half
# of a deploy. It is a REHEARSAL delta — plain HTTP registry, no ECR auth, no
# image signing. The real push path (ECR + IAM + S3 gateway for layers) is
# staging's job. Never read a green push here as proof of the ECR path.
#
# Prod fidelity: builds with --no-dev (the prod runtime image — no dev tooling),
# NOT the dev-extra build. The app box runs exactly this image.
#
# Idempotent: re-running rebuilds (Docker layer cache makes it cheap) and
# re-pushes; an unchanged image is a no-op push.

REGISTRY="${REGISTRY:-10.10.10.30:5000}"
IMAGE_NAME="${IMAGE_NAME:-flowform-backend}"
IMAGE_TAG="${IMAGE_TAG:-rehearsal}"

# Fallback transport used only when REGISTRY is not directly reachable. Docker
# Desktop's daemon does not share WSL's loopback namespace, so the built image is
# streamed to the app VM instead of forwarding the registry port into WSL.
PROXMOX_SSH_TARGET="${PROXMOX_SSH_TARGET:-root@192.168.68.88}"
PROXMOX_SSH_KEY="${PROXMOX_SSH_KEY:-${HOME}/.ssh/proxmox_codex}"
PROXMOX_PRIVATE_BRIDGE="${PROXMOX_PRIVATE_BRIDGE:-vmbr10}"
PROXMOX_TEMP_BRIDGE_CIDR="${PROXMOX_TEMP_BRIDGE_CIDR:-10.10.10.1/24}"
PUSH_RELAY_SSH_TARGET="${PUSH_RELAY_SSH_TARGET:-ec2-user@10.10.10.20}"

APP_DEST="${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
ADDED_BRIDGE_ADDRESS=0
USE_PUSH_RELAY=0

log() { printf '[build-push-backend] %s\n' "$*"; }
die() { printf '[build-push-backend] ERROR: %s\n' "$*" >&2; exit 1; }

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

# Locate the repo root from this script (fixtures/registry -> ../../../.. ). Allow
# REPO_ROOT override for odd checkouts.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd -- "${SCRIPT_DIR}/../../../../.." && pwd)}"

DOCKERFILE="${REPO_ROOT}/infra/containers/dev/services/backend/backend.Dockerfile"
[[ -f "${DOCKERFILE}" ]] || die "backend Dockerfile not found at ${DOCKERFILE} (REPO_ROOT=${REPO_ROOT}; sync the repo to the dev box or set REPO_ROOT=)"
command -v docker >/dev/null 2>&1 || die "docker not found on this box"
command -v curl >/dev/null 2>&1 || die "curl not found on this box"

SSH_OPTIONS=(
  -i "${PROXMOX_SSH_KEY}"
  -o BatchMode=yes
  -o ConnectTimeout=10
  -o ServerAliveInterval=15
  -o ServerAliveCountMax=3
)
CURL_PROBE_OPTIONS=(-fsS --connect-timeout 2 --max-time 3)

prepare_push_relay() {
  local registry_host registry_port
  registry_host="${REGISTRY%:*}"
  registry_port="${REGISTRY##*:}"

  [[ "${REGISTRY}" == *:* && -n "${registry_host}" ]] || die "REGISTRY must be host:port (got ${REGISTRY})"
  [[ "${registry_port}" =~ ^[0-9]+$ ]] || die "REGISTRY port must be numeric (got ${registry_port})"
  [[ "${PROXMOX_PRIVATE_BRIDGE}" =~ ^[a-zA-Z0-9_.:-]+$ ]] || die "invalid PROXMOX_PRIVATE_BRIDGE"
  [[ "${PROXMOX_TEMP_BRIDGE_CIDR}" =~ ^[0-9.]+/[0-9]+$ ]] || die "invalid PROXMOX_TEMP_BRIDGE_CIDR"
  [[ "${APP_DEST}" =~ ^[a-zA-Z0-9._:/-]+$ ]] || die "invalid image destination ${APP_DEST}"
  [[ -f "${PROXMOX_SSH_KEY}" ]] || die "Proxmox SSH key not found at ${PROXMOX_SSH_KEY}"
  command -v ssh >/dev/null 2>&1 || die "ssh not found on this box"

  log "registry is private; preparing temporary image relay through ${PROXMOX_SSH_TARGET}"
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

  # Rehearsal VMs are routinely rebuilt, so use an invocation-local trust
  # boundary for their host key. The stable Proxmox jump host remains checked
  # against the operator's normal known_hosts file.
  ssh "${SSH_OPTIONS[@]}" \
    -o UserKnownHostsFile=/dev/null \
    -o StrictHostKeyChecking=no \
    -o "ProxyCommand=ssh -i ${PROXMOX_SSH_KEY} -o BatchMode=yes -W %h:%p ${PROXMOX_SSH_TARGET}" \
    "${PUSH_RELAY_SSH_TARGET}" \
    "curl -fsS --connect-timeout 2 --max-time 5 'http://${REGISTRY}/v2/' >/dev/null && sudo docker info >/dev/null" \
    || die "app VM relay ${PUSH_RELAY_SSH_TARGET} cannot reach the registry or Docker"

  USE_PUSH_RELAY=1
  log "temporary image relay is ready through ${PUSH_RELAY_SSH_TARGET}"
}

# Prefer the direct path from a dual-homed operator VM. WSL/LAN workstations use
# the temporary SSH image relay without exposing the registry to the LAN.
if ! curl "${CURL_PROBE_OPTIONS[@]}" "http://${REGISTRY}/v2/" >/dev/null 2>&1; then
  prepare_push_relay
fi

DEST="${APP_DEST}"

log "building ${DEST} from ${DOCKERFILE} (context=${REPO_ROOT}, --no-dev prod image)"
# Default UV_SYNC_FLAGS in the Dockerfile is already --no-dev; pass explicitly to
# make the prod-runtime intent unmistakable and immune to a Dockerfile default change.
docker build \
  -f "${DOCKERFILE}" \
  --build-arg UV_SYNC_FLAGS="--no-dev" \
  -t "${DEST}" \
  "${REPO_ROOT}"

log "pushing ${DEST}"
if (( USE_PUSH_RELAY == 1 )); then
  docker image save "${DEST}" | ssh "${SSH_OPTIONS[@]}" \
    -o UserKnownHostsFile=/dev/null \
    -o StrictHostKeyChecking=no \
    -o "ProxyCommand=ssh -i ${PROXMOX_SSH_KEY} -o BatchMode=yes -W %h:%p ${PROXMOX_SSH_TARGET}" \
    "${PUSH_RELAY_SSH_TARGET}" \
    "sudo docker image load >/dev/null && sudo docker push '${APP_DEST}'"
else
  docker push "${DEST}"
fi

log "done. Registry catalog:"
if (( USE_PUSH_RELAY == 1 )); then
  ssh "${SSH_OPTIONS[@]}" \
    -o UserKnownHostsFile=/dev/null \
    -o StrictHostKeyChecking=no \
    -o "ProxyCommand=ssh -i ${PROXMOX_SSH_KEY} -o BatchMode=yes -W %h:%p ${PROXMOX_SSH_TARGET}" \
    "${PUSH_RELAY_SSH_TARGET}" \
    "curl -fsS --connect-timeout 2 --max-time 10 'http://${REGISTRY}/v2/_catalog'" | sed 's/^/  /'
else
  curl -fsS --connect-timeout 2 --max-time 10 "http://${REGISTRY}/v2/_catalog" | sed 's/^/  /'
fi
log "app box (220) BACKEND_IMAGE should be: ${APP_DEST}"
