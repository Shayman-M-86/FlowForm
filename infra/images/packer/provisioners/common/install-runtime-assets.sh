#!/usr/bin/env bash
set -Eeuo pipefail
. /tmp/flowform-image-lib.sh

# Install the host convergence assets staged by the preceding file provisioner.
#
# These are the bootstrap entry points and the Compose definitions they run.
# They are baked rather than fetched at boot so a host needs no artifact store
# and no network path to converge: user data only writes its inputs and runs
# the script. The trade-off is that changing a bootstrap script or Compose file
# requires a new image, which is why they live here beside the host packages
# they depend on rather than being treated as release artifacts.
#
# The layout under /opt/flowform/repo mirrors the repository, because each
# bootstrap script derives its own REPO_ROOT and Compose defaults from its
# location.

log "installing FlowForm runtime assets"

STAGED="/tmp/flowform-runtime-assets"
TARGET="/opt/flowform/repo"

test -d "${STAGED}" || die "runtime assets were not staged at ${STAGED}"

rm -rf "${TARGET}"
install -d -m 0755 "${TARGET}"
cp -a "${STAGED}/." "${TARGET}/"
rm -rf "${STAGED}"

chown -R root:root "${TARGET}"
# Directories traversable and files readable by any host process; only root
# writes. The bootstrap entry points must stay executable — user data invokes
# them directly.
find "${TARGET}" -type d -exec chmod 0755 {} +
find "${TARGET}" -type f -exec chmod 0644 {} +
chmod 0755 "${TARGET}"/infra/deployment/bootstrap/bootstrap-app.sh
chmod 0755 "${TARGET}"/infra/deployment/bootstrap/bootstrap-proxy.sh
chmod 0755 "${TARGET}"/infra/deployment/bootstrap/bootstrap-db.sh

# Fail the build rather than ship an image whose bootstrap cannot resolve its
# own Compose files.
for required in \
  "infra/deployment/bootstrap/bootstrap-app.sh" \
  "infra/deployment/bootstrap/bootstrap-proxy.sh" \
  "infra/deployment/bootstrap/bootstrap-common.sh" \
  "infra/containers/runtime/compose/app.yml" \
  "infra/containers/runtime/compose/proxy.yml" \
  "infra/containers/runtime/services/alloy/config.alloy" \
  "infra/containers/runtime/services/alloy-app/config.alloy" \
  "infra/containers/runtime/services/squid/squid.conf" \
  "infra/containers/strategies/aws/compose/proxy.override.yml"
do
  test -e "${TARGET}/${required}" || die "runtime assets are missing ${required}"
done

log "runtime assets installed at ${TARGET}"
