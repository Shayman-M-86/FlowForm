#!/usr/bin/env bash

# Compatibility shim. The retry wrappers (retry_with_backoff, aws_cli_retry) now
# live in bootstrap-common.sh alongside the rest of the shared bootstrap library.
# This file is kept so existing `source .../aws-cli-retry.sh` lines and the
# cloud-init write_files / locals.tf entries that reference it keep working
# unchanged — it simply pulls in the common library, which is co-located in the
# same baked directory. Double-sourcing is a no-op (common self-guards).

_AWS_CLI_RETRY_SHIM_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=bootstrap-common.sh
source "${_AWS_CLI_RETRY_SHIM_DIR}/bootstrap-common.sh"
