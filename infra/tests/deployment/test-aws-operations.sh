#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
OPERATIONS="${REPO_ROOT}/infra/deployment/aws/operations"

mapfile -t scripts < <(find "${OPERATIONS}" -type f -name '*.sh' ! -path '*/_lib/*' | sort)
[[ ${#scripts[@]} -ge 10 ]] || {
  printf 'expected the AWS operation boundaries to be present\n' >&2
  exit 1
}

for script in "${scripts[@]}" "${OPERATIONS}/_lib/common.sh"; do
  bash -n "${script}"
done

for script in "${scripts[@]}"; do
  [[ -x "${script}" ]] || {
    printf 'operation is not executable: %s\n' "${script}" >&2
    exit 1
  }
  "${script}" --help >/dev/null
done

actual="$(
  FLOWFORM_IMAGE_TOOL=/bin/echo \
    "${OPERATIONS}/machine-images/build.sh" app --syntax-only
)"
[[ "${actual}" == "build aws app --syntax-only" ]]

actual="$(
  FLOWFORM_IMAGE_TOOL=/bin/echo \
    "${OPERATIONS}/machine-images/publish.sh" \
      --environment staging --role app --dry-run
)"
[[ "${actual}" == "publish aws --environment staging --role app --dry-run" ]]

set +e
todo_output="$("${OPERATIONS}/configuration/update-role.sh" 2>&1)"
todo_status=$?
set -e
[[ ${todo_status} -eq 3 ]]
[[ "${todo_output}" == TODO:* ]]

printf 'AWS operations boundary checks passed.\n'
