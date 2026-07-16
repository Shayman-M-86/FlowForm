#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
"${here}/test-create-vms.sh"
"${here}/test-activation-order.sh"
"${here}/test-activation-failures.sh"
