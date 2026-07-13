#!/usr/bin/env bash
set -Eeuo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}/image-factory/packer"
packer fmt -check -recursive .
packer init .
packer validate -syntax-only .
"${repo_root}/tests/images/inspect-layout.sh"
