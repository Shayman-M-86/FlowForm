#!/usr/bin/env bash
set -Eeuo pipefail
# The golden build writes a shared manifest for both platform builders.
manifest="${1:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../packer/manifests" && pwd)/packer-manifest.json}"
[[ -f "${manifest}" ]] || { echo "manifest not found: ${manifest}" >&2; exit 1; }
jq -r '
  .builds
  | map(select(.builder_type == "amazon-ebs"))
  | last
  | .artifact_id
  | split(":")
  | .[1]
' "${manifest}"
