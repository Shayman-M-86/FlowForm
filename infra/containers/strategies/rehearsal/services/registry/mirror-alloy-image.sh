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

ADDED_BRIDGE_ADDRESS=0

log() { printf '[mirror-alloy] %s\n' "$*"; }
die() { printf '[mirror-alloy] ERROR: %s\n' "$*" >&2; exit 1; }

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

SSH_OPTIONS=(
  -i "${PROXMOX_SSH_KEY}"
  -o BatchMode=yes
  -o ConnectTimeout=10
  -o ServerAliveInterval=15
  -o ServerAliveCountMax=3
)

relay_ssh() {
  ssh "${SSH_OPTIONS[@]}" \
    -o UserKnownHostsFile=/dev/null \
    -o StrictHostKeyChecking=no \
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

  relay_ssh \
    "curl -fsS --connect-timeout 3 --max-time 5 --proxy '${SQUID_PROXY_URL}' 'https://${REGISTRY_HOST}/v2/' >/dev/null && sudo docker info >/dev/null" \
    || die "app VM relay ${PUSH_RELAY_SSH_TARGET} cannot reach https://${REGISTRY_HOST} through Squid or Docker is down"

  log "temporary image relay is ready through ${PUSH_RELAY_SSH_TARGET}"
}

log "pulling ${SOURCE_IMAGE} from Docker Hub"
docker pull "${SOURCE_IMAGE}"
log "retagging -> ${DEST_IMAGE}"
docker tag "${SOURCE_IMAGE}" "${DEST_IMAGE}"

prepare_push_relay

log "streaming ${DEST_IMAGE} to the app VM and pushing through Squid"
docker image save "${DEST_IMAGE}" \
  | relay_ssh "sudo docker image load >/dev/null && sudo docker push '${DEST_IMAGE}'"

log "done. Registry catalog:"
relay_ssh \
  "curl -fsS --connect-timeout 3 --max-time 10 --proxy '${SQUID_PROXY_URL}' 'https://${REGISTRY_HOST}/v2/_catalog'" \
  | sed 's/^/  /'
log "app box (220) ALLOY_IMAGE should be: ${DEST_IMAGE}"
