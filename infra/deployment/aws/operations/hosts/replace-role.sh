#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../_lib/common.sh
source "${SCRIPT_DIR}/../_lib/common.sh"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  printf 'Usage: %s --environment <staging|prod> --role <app|proxy>\n' "${0##*/}"
  exit 0
fi

operation_todo "role-specific EC2 replacement is not implemented. ApplicationStack currently owns both hosts; publish the role AMI and use stacks/deploy-application.sh until replacement ownership is separated."

