#!/usr/bin/env bash
set -Eeuo pipefail
. /tmp/flowform-image-lib.sh

compose_dir="/tmp/flowform-fixture-compose"
inventory_dir="/var/lib/flowform/image-fixtures"

mapfile -t images < <(
  for compose_file in "${compose_dir}"/*.yml; do
    docker compose -f "${compose_file}" config --images
  done | sort -u
)

(( ${#images[@]} > 0 )) || {
  echo "No container images were found in ${compose_dir}" >&2
  exit 1
}

log "preloading ${#images[@]} LocalStack fixture container images"
systemctl start docker
for image in "${images[@]}"; do
  log "pulling ${image}"
  docker pull "${image}"
  docker image inspect "${image}" >/dev/null
done

install -d -m 0755 "${inventory_dir}"
printf '%s\n' "${images[@]}" >"${inventory_dir}/images.txt"
docker save --output "${inventory_dir}/images.tar" "${images[@]}"
chmod 0644 "${inventory_dir}/images.txt" "${inventory_dir}/images.tar"

# Leave no running build-time services or containers. The image layers remain
# in Docker's content store and Compose starts the services at runtime.
systemctl stop docker docker.socket containerd || true
log "fixture images preloaded and archived"
