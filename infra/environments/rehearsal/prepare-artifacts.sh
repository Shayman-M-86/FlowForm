#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage: prepare-artifacts.sh --upload PVE_SSH_TARGET [options]

Builds a checksum-protected offline OCI/Docker bundle for the Proxmox rehearsal
and uploads it to the Proxmox host staging area.

Options:
  --upload TARGET    Required SSH target, for example root@pve.example.lan
  --release SHA      Commit to build (default: current HEAD)
  --output-dir DIR   Local generated output directory
  --allow-dirty      Record and permit a dirty working tree
  --help             Show this help
USAGE
}

log() { printf '[prepare-artifacts] %s\n' "$*"; }
die() { printf '[prepare-artifacts] ERROR: %s\n' "$*" >&2; exit 1; }

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
LOCK_FILE="${SCRIPT_DIR}/artifacts/images.lock"
# shellcheck source=/dev/null
. "${LOCK_FILE}"

upload=""
release=""
output_dir=""
allow_dirty=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --upload) upload="${2:-}"; shift 2 ;;
    --release) release="${2:-}"; shift 2 ;;
    --output-dir) output_dir="${2:-}"; shift 2 ;;
    --allow-dirty) allow_dirty=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

[[ -n "${upload}" ]] || die "--upload is required"
for command in docker git jq sha256sum ssh scp; do
  command -v "${command}" >/dev/null 2>&1 || die "required command not found: ${command}"
done
docker info >/dev/null 2>&1 || die "Docker daemon is unavailable"

head_commit="$(git -C "${REPO_ROOT}" rev-parse HEAD)"
release="${release:-${head_commit}}"
[[ "${release}" =~ ^[0-9a-f]{40}$ ]] || die "--release must be a full Git commit SHA"
git -C "${REPO_ROOT}" cat-file -e "${release}^{commit}" 2>/dev/null || die "release commit not found: ${release}"
dirty=false
if [[ -n "$(git -C "${REPO_ROOT}" status --porcelain)" ]]; then
  dirty=true
  [[ "${allow_dirty}" == "1" ]] || die "working tree is dirty; commit changes or pass --allow-dirty"
fi
[[ "${release}" == "${head_commit}" ]] || die "checkout ${release} before preparing its backend artifact"

release_short="${release:0:12}"
output_dir="${output_dir:-${REPO_ROOT}/infra/.generated/rehearsal/artifacts/${release_short}}"
install -d -m 0750 "${output_dir}"
archive="${output_dir}/rehearsal-images.tar"
manifest="${output_dir}/manifest.json"
checksums="${output_dir}/SHA256SUMS"
backend_tag="flowform-backend:${release}"

pull_and_tag() {
  local immutable_ref="$1" stable_ref="$2"
  log "pulling ${immutable_ref}"
  docker pull --platform linux/amd64 "${immutable_ref}"
  docker tag "${immutable_ref}" "${stable_ref}"
}

pull_and_tag "${LOCALSTACK_IMAGE}" localstack/localstack:3
pull_and_tag "${REGISTRY_IMAGE}" registry:2
pull_and_tag "${CADDY_IMAGE}" caddy:2-alpine
pull_and_tag "${POSTGRES_IMAGE}" postgres:17

dockerfile="${REPO_ROOT}/infra/environments/development/compose/backend.Dockerfile"
log "building backend ${backend_tag}"
docker build --platform linux/amd64 \
  -f "${dockerfile}" \
  --build-arg UV_SYNC_FLAGS=--no-dev \
  --label "org.opencontainers.image.revision=${release}" \
  -t "${backend_tag}" \
  "${REPO_ROOT}"
backend_image_id="$(docker image inspect --format '{{.Id}}' "${backend_tag}")"

log "writing offline image bundle"
docker save --output "${archive}.tmp" \
  localstack/localstack:3 registry:2 caddy:2-alpine postgres:17 "${backend_tag}"
mv "${archive}.tmp" "${archive}"
archive_sha256="$(sha256sum "${archive}" | awk '{print $1}')"

jq -n \
  --arg schema "flowform.rehearsal-artifact-manifest/1" \
  --argjson contract_version "${IMAGE_CONTRACT_VERSION}" \
  --arg release "${release}" \
  --argjson dirty "${dirty}" \
  --arg archive "$(basename "${archive}")" \
  --arg archive_sha256 "${archive_sha256}" \
  --arg localstack "${LOCALSTACK_IMAGE}" \
  --arg registry "${REGISTRY_IMAGE}" \
  --arg caddy "${CADDY_IMAGE}" \
  --arg postgres "${POSTGRES_IMAGE}" \
  --arg backend "${backend_tag}" \
  --arg backend_image_id "${backend_image_id}" \
  --arg created_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{schema:$schema, image_contract_version:$contract_version, release:$release,
    dirty:$dirty, archive:{file:$archive, sha256:$archive_sha256},
    images:{localstack:$localstack, registry:$registry, caddy:$caddy,
      postgres:$postgres, backend:$backend, backend_image_id:$backend_image_id},
    created_at:$created_at}' > "${manifest}"

(
  cd "${output_dir}"
  sha256sum "$(basename "${archive}")" "$(basename "${manifest}")" > "$(basename "${checksums}")"
)
chmod 0640 "${archive}" "${manifest}" "${checksums}"

remote_dir="/var/lib/flowform/rehearsal/artifacts/${release_short}"
ssh "${upload}" install -d -m 0700 "${remote_dir}"
scp "${archive}" "${manifest}" "${checksums}" "${upload}:${remote_dir}/"
log "uploaded artifact set to ${upload}:${remote_dir}"
log "artifact manifest: ${manifest}"
