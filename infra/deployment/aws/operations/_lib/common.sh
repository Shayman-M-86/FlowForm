#!/usr/bin/env bash

OPERATIONS_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
AWS_DEPLOYMENT_DIR="$(cd -- "${OPERATIONS_DIR}/.." && pwd)"
REPO_ROOT="$(cd -- "${AWS_DEPLOYMENT_DIR}/../../.." && pwd)"

FLOWFORM_IMAGE_TOOL="${FLOWFORM_IMAGE_TOOL:-${REPO_ROOT}/infra/machine-images/tooling/image}"
FLOWFORM_CONTAINER_PUBLISHER="${FLOWFORM_CONTAINER_PUBLISHER:-${AWS_DEPLOYMENT_DIR}/scripts/publish-staging-images.sh}"
FLOWFORM_CDK_DIR="${FLOWFORM_CDK_DIR:-${AWS_DEPLOYMENT_DIR}/cdk}"

operation_die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 2
}

operation_todo() {
  printf 'TODO: %s\n' "$*" >&2
  exit 3
}

require_executable() {
  [[ -x "$1" ]] || operation_die "required executable is unavailable: $1"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 \
    || operation_die "required command is unavailable: $1"
}

validate_environment() {
  case "$1" in
    dev|staging|prod) ;;
    *) operation_die "environment must be dev, staging, or prod" ;;
  esac
}

validate_host_role() {
  case "$1" in
    app|proxy) ;;
    *) operation_die "role must be app or proxy" ;;
  esac
}

