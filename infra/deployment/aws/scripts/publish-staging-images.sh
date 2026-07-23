#!/usr/bin/env bash
#
# Validate or publish the four immutable linux/amd64 staging runtime images.
# Publication only writes ECR images and a local release manifest. It does not
# select runtime SSM parameters, bootstrap hosts, or deploy infrastructure.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../.." && pwd)"
SOURCE_MANIFEST="${SOURCE_MANIFEST:-${REPO_ROOT}/infra/containers/strategies/aws/image-sources.json}"
RELEASE_MANIFEST_PATH="${RELEASE_MANIFEST_PATH:-${REPO_ROOT}/staging-image-release.json}"
PUBLISH_TEMP_DIR=""

cleanup_temp_dir() {
  if [[ -n "${PUBLISH_TEMP_DIR}" && -d "${PUBLISH_TEMP_DIR}" ]]; then
    rm -rf -- "${PUBLISH_TEMP_DIR}"
  fi
}

trap cleanup_temp_dir EXIT

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command is unavailable: $1"
}

manifest_value() {
  jq -er "$1" "${SOURCE_MANIFEST}"
}

validate_source() {
  local image_name="$1"
  local source_json="$2"
  local reference index_digest platform_digest resolved

  reference="$(jq -er '.reference' <<<"${source_json}")"
  index_digest="$(jq -er '.index_digest' <<<"${source_json}")"
  platform_digest="$(jq -er '.platform_digest' <<<"${source_json}")"

  [[ "${reference}" != *"@sha256:"* ]] \
    || die "${image_name} source reference must keep its digest in index_digest"
  [[ "${reference}" != *":latest" ]] \
    || die "${image_name} source reference must not use latest"
  [[ "${index_digest}" =~ ^sha256:[0-9a-f]{64}$ ]] \
    || die "${image_name} has an invalid index digest"
  [[ "${platform_digest}" =~ ^sha256:[0-9a-f]{64}$ ]] \
    || die "${image_name} has an invalid platform digest"

  resolved="$(
    docker buildx imagetools inspect "${reference}@${index_digest}" --raw \
      | jq -er --arg digest "${platform_digest}" '
          .manifests[]
          | select(
              .platform.os == "linux"
              and .platform.architecture == "amd64"
              and .digest == $digest
            )
          | .digest
        '
  )" || die "${image_name} source index does not contain the declared linux/amd64 digest"
  [[ "${resolved}" == "${platform_digest}" ]] \
    || die "${image_name} resolved an unexpected platform digest"
}

validate_manifest() {
  require_command docker
  require_command jq
  [[ -f "${SOURCE_MANIFEST}" ]] || die "source manifest not found: ${SOURCE_MANIFEST}"

  jq -e '
    .schema_version == 1
    and .platform == {
      "os": "linux",
      "architecture": "amd64",
      "buildx": "linux/amd64"
    }
    and (.aws.account_id | test("^[0-9]{12}$"))
    and (.aws.region | type == "string" and length > 0)
    and (.images | keys == ["alloy", "backend", "caddy", "squid"])
    and ([.images[].repository] | sort == [
      "flowform-staging-alloy",
      "flowform-staging-backend",
      "flowform-staging-caddy",
      "flowform-staging-squid"
    ])
    and (.images.backend.kind == "build")
    and (.images.caddy.kind == "build")
    and (.images.squid.kind == "mirror")
    and (.images.alloy.kind == "mirror")
  ' "${SOURCE_MANIFEST}" >/dev/null \
    || die "source manifest structure or staging repository set is invalid"

  local image_name kind dockerfile source_json reference index_digest
  for image_name in backend caddy squid alloy; do
    kind="$(manifest_value ".images.${image_name}.kind")"
    if [[ "${kind}" == "build" ]]; then
      dockerfile="$(manifest_value ".images.${image_name}.dockerfile")"
      [[ -f "${REPO_ROOT}/${dockerfile}" ]] \
        || die "${image_name} Dockerfile not found: ${dockerfile}"
      while IFS= read -r source_json; do
        validate_source "${image_name}" "${source_json}"
        reference="$(jq -er '.reference' <<<"${source_json}")"
        index_digest="$(jq -er '.index_digest' <<<"${source_json}")"
        grep -Fq "${reference#docker.io/library/}@${index_digest}" "${REPO_ROOT}/${dockerfile}" \
          || grep -Fq "${reference}@${index_digest}" "${REPO_ROOT}/${dockerfile}" \
          || die "${image_name} Dockerfile does not use declared source ${reference}@${index_digest}"
      done < <(jq -c ".images.${image_name}.sources[]" "${SOURCE_MANIFEST}")
    else
      source_json="$(jq -c ".images.${image_name}.source" "${SOURCE_MANIFEST}")"
      validate_source "${image_name}" "${source_json}"
    fi
  done

  printf 'Validated immutable staging image sources for linux/amd64.\n'
}

assert_tag_absent() {
  local repository="$1"
  local tag="$2"
  local error_file="$3"

  if aws ecr describe-images \
    --repository-name "${repository}" \
    --image-ids "imageTag=${tag}" \
    >/dev/null 2>"${error_file}"; then
    die "immutable target already exists: ${repository}:${tag}"
  fi
  grep -q 'ImageNotFoundException' "${error_file}" \
    || {
      sed -n '1,8p' "${error_file}" >&2
      die "could not prove target tag is absent in ${repository}"
    }
}

wait_for_digest() {
  local repository="$1"
  local tag="$2"
  local digest attempt

  for attempt in {1..15}; do
    digest="$(
      aws ecr describe-images \
        --repository-name "${repository}" \
        --image-ids "imageTag=${tag}" \
        --query 'imageDetails[0].imageDigest' \
        --output text 2>/dev/null || true
    )"
    if [[ "${digest}" =~ ^sha256:[0-9a-f]{64}$ ]]; then
      printf '%s\n' "${digest}"
      return 0
    fi
    sleep 2
  done
  die "ECR did not report a digest for ${repository}:${tag}"
}

metadata_digest() {
  local kind="$1"
  local metadata_file="$2"
  local selector digest

  if [[ "${kind}" == "build" ]]; then
    selector='."containerimage.digest"'
  else
    # `imagetools create` reports an OCI descriptor rather than the flat
    # build-result field emitted by `buildx build`.
    selector='."containerimage.descriptor".digest'
  fi
  digest="$(jq -er "${selector}" "${metadata_file}")" \
    || die "${kind} publisher metadata did not contain an image digest"
  [[ "${digest}" =~ ^sha256:[0-9a-f]{64}$ ]] \
    || die "${kind} publisher metadata contained an invalid image digest"
  printf '%s\n' "${digest}"
}

publish_images() {
  require_command aws
  validate_manifest

  local account_id region platform release_sha tag registry caller_account
  local temp_dir image_name kind repository target metadata_file expected_digest
  local actual_digest source_json source_ref dockerfile context entry

  account_id="$(manifest_value '.aws.account_id')"
  region="$(manifest_value '.aws.region')"
  platform="$(manifest_value '.platform.buildx')"
  release_sha="${RELEASE_COMMIT_SHA:-${GITHUB_SHA:-}}"
  [[ "${release_sha}" =~ ^[0-9a-f]{40}$ ]] \
    || die "RELEASE_COMMIT_SHA or GITHUB_SHA must be a lowercase 40-character commit SHA"
  tag="git-${release_sha}"
  registry="${account_id}.dkr.ecr.${region}.amazonaws.com"
  caller_account="$(aws sts get-caller-identity --query Account --output text)"
  [[ "${caller_account}" == "${account_id}" ]] \
    || die "AWS caller account ${caller_account} does not match manifest account ${account_id}"

  PUBLISH_TEMP_DIR="$(mktemp -d)"
  temp_dir="${PUBLISH_TEMP_DIR}"

  for image_name in backend caddy squid alloy; do
    repository="$(manifest_value ".images.${image_name}.repository")"
    assert_tag_absent "${repository}" "${tag}" "${temp_dir}/${image_name}-preflight.err"
  done

  aws ecr get-login-password --region "${region}" \
    | docker login --username AWS --password-stdin "${registry}" >/dev/null

  printf '[]\n' >"${temp_dir}/release-entries.json"
  for image_name in backend caddy squid alloy; do
    kind="$(manifest_value ".images.${image_name}.kind")"
    repository="$(manifest_value ".images.${image_name}.repository")"
    target="${registry}/${repository}:${tag}"
    metadata_file="${temp_dir}/${image_name}-metadata.json"

    if [[ "${kind}" == "build" ]]; then
      dockerfile="$(manifest_value ".images.${image_name}.dockerfile")"
      context="$(manifest_value ".images.${image_name}.context")"
      docker buildx build \
        --platform "${platform}" \
        --file "${REPO_ROOT}/${dockerfile}" \
        --tag "${target}" \
        --push \
        --provenance=false \
        --sbom=false \
        --metadata-file "${metadata_file}" \
        "${REPO_ROOT}/${context}"
      expected_digest="$(metadata_digest "${kind}" "${metadata_file}")"
      entry="$(
        jq -n \
          --arg name "${image_name}" \
          --arg kind "${kind}" \
          --arg target_tag "${target}" \
          --arg dockerfile "${dockerfile}" \
          --argjson sources "$(jq ".images.${image_name}.sources" "${SOURCE_MANIFEST}")" \
          '{
            name: $name,
            kind: $kind,
            target_tag: $target_tag,
            dockerfile: $dockerfile,
            sources: $sources
          }'
      )"
    else
      source_json="$(jq -c ".images.${image_name}.source" "${SOURCE_MANIFEST}")"
      source_ref="$(
        jq -er '"\(.reference)@\(.platform_digest)"' <<<"${source_json}"
      )"
      docker buildx imagetools create \
        --prefer-index=false \
        --tag "${target}" \
        --metadata-file "${metadata_file}" \
        "${source_ref}"
      expected_digest="$(metadata_digest "${kind}" "${metadata_file}")"
      entry="$(
        jq -n \
          --arg name "${image_name}" \
          --arg kind "${kind}" \
          --arg target_tag "${target}" \
          --argjson source "${source_json}" \
          '{
            name: $name,
            kind: $kind,
            target_tag: $target_tag,
            source: $source
          }'
      )"
    fi

    actual_digest="$(wait_for_digest "${repository}" "${tag}")"
    [[ "${actual_digest}" == "${expected_digest}" ]] \
      || die "${image_name} ECR digest ${actual_digest} does not match publisher digest ${expected_digest}"
    entry="$(
      jq \
        --arg digest "${actual_digest}" \
        --arg target "${registry}/${repository}@${actual_digest}" \
        '. + {digest: $digest, target: $target}' <<<"${entry}"
    )"
    jq --argjson entry "${entry}" '. + [$entry]' \
      "${temp_dir}/release-entries.json" >"${temp_dir}/release-entries.next.json"
    mv "${temp_dir}/release-entries.next.json" "${temp_dir}/release-entries.json"
  done

  mkdir -p "$(dirname -- "${RELEASE_MANIFEST_PATH}")"
  jq -n \
    --arg commit_sha "${release_sha}" \
    --arg generated_at "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    --arg account_id "${account_id}" \
    --arg region "${region}" \
    --arg platform "${platform}" \
    --argjson images "$(jq . "${temp_dir}/release-entries.json")" \
    '{
      schema_version: 1,
      commit_sha: $commit_sha,
      generated_at: $generated_at,
      aws: {account_id: $account_id, region: $region},
      platform: $platform,
      images: $images
    }' >"${RELEASE_MANIFEST_PATH}"

  printf 'Published four immutable staging images.\nRelease manifest: %s\n' "${RELEASE_MANIFEST_PATH}"
}

case "${1:-}" in
  validate)
    validate_manifest
    ;;
  publish)
    publish_images
    ;;
  *)
    die "usage: $0 {validate|publish}"
    ;;
esac
