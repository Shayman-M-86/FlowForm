#!/usr/bin/env bash

if [[ -n "${_FLOWFORM_INSTANCE_CONTEXT_SOURCED:-}" ]]; then return; fi
_FLOWFORM_INSTANCE_CONTEXT_SOURCED=1

flowform_load_instance_context() { # app|proxy [context-path]
  local expected_role="$1"
  local context_path="${2:-${FLOWFORM_INSTANCE_CONTEXT:-/etc/flowform/instance-context.json}}"
  local context_role configuration_root

  command -v jq >/dev/null 2>&1 || {
    printf 'FlowForm instance context requires jq\n' >&2
    return 1
  }
  [[ -r "${context_path}" ]] || {
    printf 'FlowForm instance context is missing or unreadable: %s\n' "${context_path}" >&2
    return 1
  }

  jq -e '
    .schema_version == 1
    and (.environment | type == "string" and length > 0)
    and (.role == "app" or .role == "proxy")
    and (.region | test("^[a-z]{2}-[a-z]+-[0-9]+$"))
    and (.parameter_root | test("^/flowform/[a-z0-9-]+$"))
    and (.configuration_root | test("^/flowform/[a-z0-9-]+$"))
  ' "${context_path}" >/dev/null || {
    printf 'FlowForm instance context failed schema validation: %s\n' "${context_path}" >&2
    return 1
  }

  context_role="$(jq -r '.role' "${context_path}")"
  [[ "${context_role}" == "${expected_role}" ]] || {
    printf 'FlowForm AMI role is %s but instance context requests %s\n' \
      "${expected_role}" "${context_role}" >&2
    return 1
  }

  FLOWFORM_ENV="$(jq -r '.environment' "${context_path}")"
  AWS_REGION="$(jq -r '.region' "${context_path}")"
  FLOWFORM_PARAMETER_ROOT="$(jq -r '.parameter_root' "${context_path}")"
  configuration_root="$(jq -r '.configuration_root' "${context_path}")"
  FLOWFORM_SCOPE="${configuration_root##*/}"
  FLOWFORM_DEPLOYMENT_TARGET="aws"
  FLOWFORM_PLATFORM="aws"

  if [[ "${expected_role}" == "app" ]]; then
    PROXY_GATEWAY_HOST="$(jq -er '.proxy_dns_name | select(type == "string" and length > 0)' "${context_path}")"
    # Transitional aliases consumed by the existing bootstrap. They carry a
    # stable private DNS name; host port binding no longer depends on an IP.
    PROXY_PRIVATE_IP="${PROXY_GATEWAY_HOST}"
    APP_PRIVATE_IP="0.0.0.0"
    export HTTP_PROXY="http://${PROXY_GATEWAY_HOST}:3128"
    export HTTPS_PROXY="${HTTP_PROXY}"
    export NO_PROXY="localhost,127.0.0.1,169.254.169.254,.rds.amazonaws.com"
    export http_proxy="${HTTP_PROXY}" https_proxy="${HTTPS_PROXY}" no_proxy="${NO_PROXY}"
    export PROXY_GATEWAY_HOST PROXY_PRIVATE_IP APP_PRIVATE_IP
  else
    APP_UPSTREAM_HOST="$(jq -er '.app_dns_name | select(type == "string" and length > 0)' "${context_path}")"
    APP_PRIVATE_IP="${APP_UPSTREAM_HOST}"
    PROXY_PRIVATE_IP="0.0.0.0"
    export APP_UPSTREAM_HOST APP_PRIVATE_IP PROXY_PRIVATE_IP
  fi

  export FLOWFORM_ENV AWS_REGION FLOWFORM_PARAMETER_ROOT FLOWFORM_SCOPE
  export FLOWFORM_DEPLOYMENT_TARGET FLOWFORM_PLATFORM
}
