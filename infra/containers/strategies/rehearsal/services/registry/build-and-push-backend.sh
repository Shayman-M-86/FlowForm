#!/usr/bin/env bash
set -Eeuo pipefail

# Build the FlowForm backend image and push it to the rehearsal's private
# registry. Runtime fixture images are owned by their Packer templates; this
# publication path intentionally handles only the application image.
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
#
# Startup-race tolerance: run straight after `terraform apply`, the relay path
# may not be settled — the just-added bridge address is not yet ARP-resolved, and
# the TLS shim / registry on VM 230 are the last services to come healthy. Both
# preflights retry until the stack converges instead of failing fast, so a fresh
# apply → push in one command (see proxmox/scripts/rebuild.sh) does not need a
# manual redo. A fully-up stack passes on the first attempt with no added wait.
# Optional knobs (attempts x delay seconds; defaults wait ~120s each):
#   PUSH_RELAY_MAX_ATTEMPTS (60) / PUSH_RELAY_RETRY_DELAY_SECONDS (2)
#   PUSH_PREFLIGHT_MAX_ATTEMPTS (60) / PUSH_PREFLIGHT_RETRY_DELAY_SECONDS (2)

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
ADDED_BRIDGE_ADDRESS=0

log() { printf '[build-push-backend] %s\n' "$*"; }
die() { printf '[build-push-backend] ERROR: %s\n' "$*" >&2; exit 1; }

# Retry a command with fixed-delay backoff. This script runs on the operator's
# box right after `terraform apply`, so the app VM's SSH, Squid, and the TLS
# shim on VM 230 may still be seconds from ready — a fail-fast preflight turns
# that ordinary startup race into a spurious failure the operator has to redo by
# hand. Mirrors the bootstrap scripts' retry_with_backoff: returns immediately on
# the first success (a fully-up stack adds no latency), and on exhaustion returns
# the last failure so callers still fail closed.
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

# How long to wait for the freshly-applied stack to converge before giving up.
# The shim/registry on VM 230 are the slowest to come healthy after apply.
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

# Locate the repo root from this script (strategies/rehearsal/services/registry
# -> ../../../../../..). Allow
# REPO_ROOT override for odd checkouts.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd -- "${SCRIPT_DIR}/../../../../../.." && pwd)}"
DOCKERFILE="${REPO_ROOT}/infra/containers/images/backend/backend.Dockerfile"
[[ -f "${DOCKERFILE}" ]] || die "backend Dockerfile not found at ${DOCKERFILE} (REPO_ROOT=${REPO_ROOT}; sync the repo to the dev box or set REPO_ROOT=)"
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

  # Reachability: the temporary bridge address was just added, so the app VM may
  # not have ARP-resolved it yet — the SSH ProxyCommand's first connect can fail
  # with "No route to host" purely on timing. Retry a no-op relay login until the
  # path settles rather than dying on that race.
  retry_with_backoff "app VM relay SSH (${PUSH_RELAY_SSH_TARGET})" \
    "${RELAY_MAX_ATTEMPTS}" "${RELAY_RETRY_DELAY_SECONDS}" \
    relay_ssh true \
    || die "app VM relay ${PUSH_RELAY_SSH_TARGET} unreachable via ${PROXMOX_SSH_TARGET} after ${RELAY_MAX_ATTEMPTS} attempts"

  # Preflight: the app VM must reach the registry over HTTPS through Squid (the
  # exact push path) and have a working Docker daemon. The app VM trusts the
  # rehearsal CA via its system bundle, so no --cacert / -k here. Retried because
  # right after `terraform apply` the TLS shim / registry on VM 230 are the last
  # services to come healthy: a fresh stack often needs a few seconds before this
  # path succeeds, which is a wait, not a failure.
  retry_with_backoff "registry reachable through Squid" \
    "${PREFLIGHT_MAX_ATTEMPTS}" "${PREFLIGHT_RETRY_DELAY_SECONDS}" \
    relay_ssh \
    "curl -fsS --connect-timeout 3 --max-time 5 --proxy '${SQUID_PROXY_URL}' 'https://${REGISTRY_HOST}/v2/' >/dev/null && sudo docker info >/dev/null" \
    || die "app VM relay ${PUSH_RELAY_SSH_TARGET} cannot reach https://${REGISTRY_HOST} through Squid or Docker is down after ${PREFLIGHT_MAX_ATTEMPTS} attempts"

  log "temporary image relay is ready through ${PUSH_RELAY_SSH_TARGET}"
}

# The registry is only reachable from the app VM through Squid — always relay.
prepare_push_relay

DEST="${APP_DEST}"
PUSH_IMAGES=("${APP_DEST}")

log "building ${DEST} from ${DOCKERFILE} (context=${REPO_ROOT}, --no-dev prod image)"
# Default UV_SYNC_FLAGS in the Dockerfile is already --no-dev; pass explicitly to
# make the prod-runtime intent unmistakable and immune to a Dockerfile default change.
docker build \
  -f "${DOCKERFILE}" \
  --build-arg UV_SYNC_FLAGS="--no-dev" \
  -t "${DEST}" \
  "${REPO_ROOT}"

log "pushing the rehearsal backend image via the app VM (through Squid)"
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
