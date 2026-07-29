#!/usr/bin/env bash
set -Eeuo pipefail
. /tmp/flowform-image-lib.sh

role="${FLOWFORM_IMAGE_ROLE:?set FLOWFORM_IMAGE_ROLE to app or proxy}"
case "${role}" in app|proxy) ;; *) die "invalid FlowForm image role: ${role}" ;; esac

staged="/tmp/flowform-role-assets"
shared_host_target="/opt/flowform/host"
role_host_target="/opt/flowform/role"
runtime_target="/opt/flowform/runtime"
unit="flowform-${role}.service"

test -d "${staged}/shared-host" || die "shared host assets were not staged"
test -d "${staged}/role-host" || die "${role} host assets were not staged"
test -d "${staged}/runtime-common" || die "common runtime assets were not staged"
test -f "${staged}/runtime-compose/${role}.yml" \
  || die "${role} runtime Compose topology was not staged"

rm -rf "${shared_host_target}" "${role_host_target}" "${runtime_target}"
install -d -m 0755 \
  "${shared_host_target}" \
  "${role_host_target}" \
  "${runtime_target}/common" \
  "${runtime_target}/compose"
cp -a "${staged}/shared-host/." "${shared_host_target}/"
cp -a "${staged}/role-host/." "${role_host_target}/"
cp -a "${staged}/runtime-common/." "${runtime_target}/common/"
install -m 0644 \
  "${staged}/runtime-compose/${role}.yml" \
  "${runtime_target}/compose/${role}.yml"
install -m 0644 \
  "${role_host_target}/systemd/${unit}" \
  "/etc/systemd/system/${unit}"
rm -rf "${staged}"

chown -R root:root \
  "${shared_host_target}" \
  "${role_host_target}" \
  "${runtime_target}" \
  "/etc/systemd/system/${unit}"
find "${shared_host_target}" "${role_host_target}" "${runtime_target}" \
  -type d -exec chmod 0755 {} +
find "${shared_host_target}" "${role_host_target}" "${runtime_target}" \
  -type f -exec chmod 0644 {} +
find \
  "${shared_host_target}/bin" \
  "${role_host_target}/bin" \
  "${runtime_target}/common/scripts" \
  -type f -name '*.sh' -exec chmod 0755 {} +

systemctl daemon-reload
systemctl enable "${unit}"
log "installed ${role} role assets and enabled ${unit}"
