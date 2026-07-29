#!/usr/bin/env bash
set -Eeuo pipefail

role="${1:-}"
case "${role}" in
  app|proxy) ;;
  *) printf 'Usage: run-role.sh <app|proxy>\n' >&2; exit 2 ;;
esac

runtime_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
host_bin="${FLOWFORM_HOST_BIN:-/opt/flowform/host/bin}"
role_root="${FLOWFORM_ROLE_ROOT:-/opt/flowform/role}"

# shellcheck source=/opt/flowform/host/bin/load-instance-context.sh
source "${host_bin}/load-instance-context.sh"
# shellcheck source=load-release-manifest.sh
source "${runtime_script_dir}/load-release-manifest.sh"

flowform_load_instance_context "${role}"
flowform_load_release_manifest "${role}"

exec "${role_root}/bin/bootstrap-${role}.sh"
