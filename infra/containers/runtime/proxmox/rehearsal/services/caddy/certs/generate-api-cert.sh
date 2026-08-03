#!/usr/bin/env bash
set -Eeuo pipefail

# Compatibility entrypoint. The rehearsal command owns CA preservation,
# validation, permissions, and coordinated leaf regeneration.
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${HERE}/../../../../../../../.." && pwd)"

exec "${REPO_ROOT}/infra/deployment/proxmox/scripts/rehearsal" tls
