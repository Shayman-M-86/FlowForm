#!/usr/bin/env bash

# Shared retry wrapper for boot-time AWS CLI reads. Real AWS and the rehearsal
# use the same calls; retries mainly close the race between simultaneous VM
# startup and the LocalStack seed service becoming ready.

aws_cli_retry() {
  local description="$1"
  shift
  local attempts="${BOOTSTRAP_AWS_MAX_ATTEMPTS:-30}"
  local delay_seconds="${BOOTSTRAP_AWS_RETRY_DELAY_SECONDS:-2}"
  local attempt output

  for ((attempt = 1; attempt <= attempts; attempt++)); do
    if output="$(aws "${AWS_ARGS[@]}" "$@" 2>&1)"; then
      printf '%s' "${output}"
      return
    fi
    if ((attempt == 1 || attempt % 10 == 0)); then
      log "${description} not ready (${attempt}/${attempts}); retrying" >&2
    fi
    sleep "${delay_seconds}"
  done

  printf '[aws-cli-retry] %s failed after %s attempts: %s\n' \
    "${description}" "${attempts}" "${output}" >&2
  return 1
}
