#!/usr/bin/env bash
set -Eeuo pipefail

# Build the FlowForm backend image and push it to the rehearsal's private
# registry. Also mirror the registry-qualified third-party images named by the
# rehearsal app Compose override, so the offline app box (220) can pull every
# runtime image at bootstrap.
#
# WHERE THIS RUNS: a host with Docker, internet, the repo checkout, and SSH
# access to the Proxmox host. The registry is reached ONLY as
# https://registry.localstack.test through Squid + the TLS shim, and Squid's
# source ACL admits only the app VM (10.10.10.20/32) — so no workstation can
# push directly. This script always relays: it temporarily gives the Proxmox
# host an IP on vmbr10, streams the built image over SSH to the app VM, and the
# app daemon pushes through its proxy drop-in (CONNECT registry.localstack.test
# :443 → Squid → shim → registry). The address is removed after the push,
# including on failure.
#
# WHAT IT PROVES / DOESN'T: this is the rehearsal stand-in for the ECR push half
# of a deploy. Registry-over-HTTPS-through-Squid mirrors ECR's transport, but
# there is no ECR auth or image signing. The real push path (ECR + IAM + S3
# gateway for layers) is staging's job. Never read a green push here as proof.
#
# Prod fidelity: builds with --no-dev (the prod runtime image — no dev tooling),
# NOT the dev-extra build. The app box runs exactly this image.
#
# Idempotent: re-running rebuilds (Docker layer cache makes it cheap) and
# re-pushes; an unchanged image is a no-op push.

REGISTRY_HOST="${REGISTRY_HOST:-registry.localstack.test}"   # no port ⇒ 443/HTTPS
IMAGE_NAME="${IMAGE_NAME:-flowform-backend}"
IMAGE_TAG="${IMAGE_TAG:-rehearsal}"

# The registry is never LAN-reachable; the built image is streamed to the app VM
# and pushed from there, through Squid. Docker Desktop's daemon also does not
# share WSL's loopback namespace, so relaying is the only path either way.
PROXMOX_SSH_TARGET="${PROXMOX_SSH_TARGET:-root@192.168.68.88}"
PROXMOX_SSH_KEY="${PROXMOX_SSH_KEY:-${HOME}/.ssh/proxmox_codex}"
PROXMOX_PRIVATE_BRIDGE="${PROXMOX_PRIVATE_BRIDGE:-vmbr10}"
PROXMOX_TEMP_BRIDGE_CIDR="${PROXMOX_TEMP_BRIDGE_CIDR:-10.10.10.1/24}"
PUSH_RELAY_SSH_TARGET="${PUSH_RELAY_SSH_TARGET:-ec2-user@10.10.10.20}"
SQUID_PROXY_URL="${SQUID_PROXY_URL:-http://10.10.10.10:3128}"

APP_DEST="${REGISTRY_HOST}/${IMAGE_NAME}:${IMAGE_TAG}"
APP_REHEARSAL_COMPOSE="${APP_REHEARSAL_COMPOSE:-}"
ADDED_BRIDGE_ADDRESS=0

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
APP_REHEARSAL_COMPOSE="${APP_REHEARSAL_COMPOSE:-${REPO_ROOT}/infra/containers/rehearsal/compose/compose.app.rehearsal.yml}"

DOCKERFILE="${REPO_ROOT}/infra/containers/dev/services/backend/backend.Dockerfile"
[[ -f "${DOCKERFILE}" ]] || die "backend Dockerfile not found at ${DOCKERFILE} (REPO_ROOT=${REPO_ROOT}; sync the repo to the dev box or set REPO_ROOT=)"
[[ -f "${APP_REHEARSAL_COMPOSE}" ]] || die "rehearsal app Compose file not found at ${APP_REHEARSAL_COMPOSE}"
command -v docker >/dev/null 2>&1 || die "docker not found on this box"
command -v ssh >/dev/null 2>&1 || die "ssh not found on this box"

SSH_OPTIONS=(
  -i "${PROXMOX_SSH_KEY}"
  -o BatchMode=yes
  -o ConnectTimeout=10
  -o ServerAliveInterval=15
  -o ServerAliveCountMax=3
)

# ssh to a rehearsal VM through the Proxmox jump host. Rehearsal VMs are
# routinely rebuilt, so their host key uses an invocation-local trust boundary;
# the stable Proxmox jump host stays checked against the normal known_hosts.
relay_ssh() {
  ssh "${SSH_OPTIONS[@]}" \
    -o UserKnownHostsFile=/dev/null \
    -o StrictHostKeyChecking=no \
    -o "ProxyCommand=ssh -i ${PROXMOX_SSH_KEY} -o BatchMode=yes -W %h:%p ${PROXMOX_SSH_TARGET}" \
    "${PUSH_RELAY_SSH_TARGET}" "$@"
}

prepare_push_relay() {
  [[ "${PROXMOX_PRIVATE_BRIDGE}" =~ ^[a-zA-Z0-9_.:-]+$ ]] || die "invalid PROXMOX_PRIVATE_BRIDGE"
  [[ "${PROXMOX_TEMP_BRIDGE_CIDR}" =~ ^[0-9.]+/[0-9]+$ ]] || die "invalid PROXMOX_TEMP_BRIDGE_CIDR"
  [[ "${APP_DEST}" =~ ^[a-zA-Z0-9._:/-]+$ ]] || die "invalid image destination ${APP_DEST}"
  [[ -f "${PROXMOX_SSH_KEY}" ]] || die "Proxmox SSH key not found at ${PROXMOX_SSH_KEY}"

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

  # Preflight: the app VM must reach the registry over HTTPS through Squid (the
  # exact push path) and have a working Docker daemon. The app VM trusts the
  # rehearsal CA via its system bundle, so no --cacert / -k here.
  relay_ssh \
    "curl -fsS --connect-timeout 3 --max-time 5 --proxy '${SQUID_PROXY_URL}' 'https://${REGISTRY_HOST}/v2/' >/dev/null && sudo docker info >/dev/null" \
    || die "app VM relay ${PUSH_RELAY_SSH_TARGET} cannot reach https://${REGISTRY_HOST} through Squid or Docker is down"

  log "temporary image relay is ready through ${PUSH_RELAY_SSH_TARGET}"
}

# The registry is only reachable from the app VM through Squid — always relay.
prepare_push_relay

DEST="${APP_DEST}"
PUSH_IMAGES=("${APP_DEST}")

# The destination references are owned by Compose. Strip only this rehearsal
# registry prefix to obtain the upstream pull reference; no versions are
# duplicated or invented here.
# Variable references (image: ${BACKEND_IMAGE:?...}) are excluded: the backend
# image is what THIS script builds and pushes as ${APP_DEST}, injected at deploy
# time — only literal third-party references need mirroring.
mapfile -t compose_registry_images < <(
  awk '$1 == "image:" && $2 !~ /\$/ {gsub(/"/, "", $2); print $2}' "${APP_REHEARSAL_COMPOSE}" \
    | sort -u
)
for registry_image in "${compose_registry_images[@]}"; do
  [[ "${registry_image}" == "${REGISTRY_HOST}/"* ]] \
    || die "rehearsal image ${registry_image} must use the private registry prefix ${REGISTRY_HOST}/"
  upstream_image="${registry_image#${REGISTRY_HOST}/}"
  log "mirroring runtime dependency ${upstream_image} as ${registry_image}"
  docker pull "${upstream_image}"
  docker tag "${upstream_image}" "${registry_image}"
  PUSH_IMAGES+=("${registry_image}")
done

log "building ${DEST} from ${DOCKERFILE} (context=${REPO_ROOT}, --no-dev prod image)"
# Default UV_SYNC_FLAGS in the Dockerfile is already --no-dev; pass explicitly to
# make the prod-runtime intent unmistakable and immune to a Dockerfile default change.
docker build \
  -f "${DOCKERFILE}" \
  --build-arg UV_SYNC_FLAGS="--no-dev" \
  -t "${DEST}" \
  "${REPO_ROOT}"

log "pushing ${#PUSH_IMAGES[@]} rehearsal images via the app VM (through Squid)"
# The app daemon's proxy drop-in tunnels the push: CONNECT registry.localstack
# .test:443 → Squid → shim → registry. registry:2 accepts anonymous pushes.
remote_push_command="sudo docker image load >/dev/null"
for image in "${PUSH_IMAGES[@]}"; do
  [[ "${image}" =~ ^[a-zA-Z0-9._:/-]+$ ]] || die "invalid image destination ${image}"
  remote_push_command+=" && sudo docker push '${image}'"
done
docker image save "${PUSH_IMAGES[@]}" | relay_ssh "${remote_push_command}"

log "done. Registry catalog:"
relay_ssh \
  "curl -fsS --connect-timeout 3 --max-time 10 --proxy '${SQUID_PROXY_URL}' 'https://${REGISTRY_HOST}/v2/_catalog'" \
  | sed 's/^/  /'
log "app box (220) BACKEND_IMAGE should be: ${APP_DEST}"
