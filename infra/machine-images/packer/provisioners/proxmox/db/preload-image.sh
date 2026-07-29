#!/usr/bin/env bash
set -Eeuo pipefail
. /tmp/flowform-image-lib.sh

compose_file="/tmp/flowform-db-compose.yml"
inventory_dir="/var/lib/flowform/image-fixtures/db"

mapfile -t images < <(docker compose -f "${compose_file}" config --images | sort -u)
(( ${#images[@]} == 1 )) \
  || die "DB fixture must declare exactly one image; found ${#images[@]}"

log "preloading ${#images[@]} database fixture image(s)"
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
tar -tf "${inventory_dir}/images.tar" | grep -Fq manifest.json \
  || die "saved DB fixture image archive has no manifest"

systemctl stop docker docker.socket containerd || true
log "database fixture image preloaded and archived"
