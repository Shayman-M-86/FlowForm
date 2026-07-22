#!/usr/bin/env bash

# Shared retry wrappers for boot-time operations. Real AWS and the rehearsal use
# the same calls; retries mainly close the race between simultaneous VM startup
# and a not-yet-ready dependency (the LocalStack seed service, or — for image
# pulls — the operator's registry push arriving after the VMs are up).

# Retry an arbitrary command with fixed-delay backoff. Captures combined
# stdout+stderr; on success prints it and returns 0, on exhaustion prints a
# diagnostic to stderr and returns 1. Callers pass a human description, the
# attempt count, the delay, and then the command + args.
#
#   retry_with_backoff "<description>" <attempts> <delay_seconds> cmd arg...
#
# Returns immediately on the first successful attempt, so a dependency that is
# already ready (the common prod case) adds no latency.
retry_with_backoff() {
  local description="$1" attempts="$2" delay_seconds="$3"
  shift 3
  local attempt output

  for ((attempt = 1; attempt <= attempts; attempt++)); do
    if output="$("$@" 2>&1)"; then
      printf '%s' "${output}"
      return 0
    fi
    if ((attempt == 1 || attempt % 10 == 0)); then
      log "${description} not ready (${attempt}/${attempts}); retrying" >&2
    fi
    sleep "${delay_seconds}"
  done

  printf '[retry] %s failed after %s attempts: %s\n' \
    "${description}" "${attempts}" "${output}" >&2
  return 1
}

# AWS-CLI-specific convenience over retry_with_backoff: prepends the shared
# AWS_ARGS (region, optional rehearsal endpoint override). Behaviour and default
# knobs are unchanged from before this helper was factored out.
aws_cli_retry() {
  local description="$1"
  shift
  retry_with_backoff "${description}" \
    "${BOOTSTRAP_AWS_MAX_ATTEMPTS:-30}" \
    "${BOOTSTRAP_AWS_RETRY_DELAY_SECONDS:-2}" \
    aws "${AWS_ARGS[@]}" "$@"
}
