#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
PYRIGHT_VERSION="1.1.411"

usage() {
    cat <<'EOF'
Usage: scripts/tools/typecheck.sh [all|tooling|backend|cdk|openapi]

Runs the repository-pinned Pyright version against one configured Python
project, or against every project when no target is supplied.
EOF
}

run_pyright() {
    local label="$1"
    local project_dir="$2"

    echo "==> Type checking ${label}"
    uvx --from "pyright==${PYRIGHT_VERSION}" pyright --project "${project_dir}"
}

check_tooling() {
    uv sync --project "${REPOSITORY_ROOT}/tools" --frozen --extra docs --extra research
    run_pyright "repository tooling" "${REPOSITORY_ROOT}"
}

check_backend() {
    uv sync --project "${REPOSITORY_ROOT}/backend" --frozen --extra dev
    run_pyright "backend" "${REPOSITORY_ROOT}/backend"
}

check_cdk() {
    uv sync --project "${REPOSITORY_ROOT}/infra/deployment/aws/cdk" --frozen --extra dev
    run_pyright "AWS CDK" "${REPOSITORY_ROOT}/infra/deployment/aws/cdk"
}

check_openapi() {
    uv sync --project "${REPOSITORY_ROOT}/tools" --frozen --extra openapi
    run_pyright "OpenAPI MCP server" "${REPOSITORY_ROOT}/tools"
}

main() {
    local target="${1:-all}"

    if [[ "$#" -gt 1 ]]; then
        usage >&2
        return 2
    fi

    case "${target}" in
        all|tooling|backend|cdk|openapi)
            ;;
        -h|--help)
            usage
            return
            ;;
        *)
            echo "Unknown type-check target: ${target}" >&2
            usage >&2
            return 2
            ;;
    esac

    case "${target}" in
        all)
            check_tooling
            check_backend
            check_cdk
            check_openapi
            ;;
        tooling)
            check_tooling
            ;;
        backend)
            check_backend
            ;;
        cdk)
            check_cdk
            ;;
        openapi)
            check_openapi
            ;;
    esac
}

main "$@"
