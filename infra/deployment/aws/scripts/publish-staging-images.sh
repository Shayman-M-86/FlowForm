#!/usr/bin/env bash
#
# Validate, publish, or promote the four immutable linux/amd64 staging runtime
# images.
#
# Publication only writes ECR images and a local release manifest. It does not
# select runtime SSM parameters, bootstrap hosts, or deploy infrastructure.
#
# Promotion is the separate, deliberate act of pointing an environment at an
# already-published release: it reads the publication manifest and writes one
# complete App manifest and one complete Proxy manifest. Keeping the two apart
# means republishing an image never moves a running environment, and promoting
# never rebuilds anything.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../.." && pwd)"
SOURCE_MANIFEST="${SOURCE_MANIFEST:-${REPO_ROOT}/infra/contracts/image-sources.json}"
RELEASE_MANIFEST_PATH="${RELEASE_MANIFEST_PATH:-${REPO_ROOT}/staging-image-release.json}"
HOST_CONTRACT="${HOST_CONTRACT:-${REPO_ROOT}/infra/contracts/runtime-hosts.json}"
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

require_relative_manifest_path() {
  local field="$1"
  local value="$2"

  [[ -n "${value}" && "${value}" != /* ]] \
    || die "${field} must be a non-empty relative path: ${value}"
  [[ ! "${value}" =~ (^|/)\.\.(/|$) ]] \
    || die "${field} must not escape its declared root: ${value}"
}

build_context_path() {
  local image_name="$1"
  local context

  context="$(manifest_value ".images.${image_name}.context")"
  require_relative_manifest_path "${image_name} build context" "${context}"
  [[ -d "${REPO_ROOT}/${context}" ]] \
    || die "${image_name} build context not found: ${context}"
  printf '%s\n' "${REPO_ROOT}/${context}"
}

build_dockerfile_path() {
  local image_name="$1"
  local context_path="$2"
  local dockerfile

  dockerfile="$(manifest_value ".images.${image_name}.dockerfile")"
  require_relative_manifest_path "${image_name} Dockerfile" "${dockerfile}"
  [[ -f "${context_path}/${dockerfile}" ]] \
    || die "${image_name} Dockerfile not found in its build context: ${dockerfile}"
  printf '%s\n' "${context_path}/${dockerfile}"
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
    and ([.images[].kind == "build" or .images[].kind == "mirror"] | all)
  ' "${SOURCE_MANIFEST}" >/dev/null \
    || die "source manifest structure or staging repository set is invalid"

  local image_name kind context_path dockerfile_path source_json reference
  local index_digest dockerfile_reference
  for image_name in backend caddy squid alloy; do
    kind="$(manifest_value ".images.${image_name}.kind")"
    if [[ "${kind}" == "build" ]]; then
      context_path="$(build_context_path "${image_name}")"
      dockerfile_path="$(build_dockerfile_path "${image_name}" "${context_path}")"
      while IFS= read -r source_json; do
        validate_source "${image_name}" "${source_json}"
        reference="$(jq -er '.reference' <<<"${source_json}")"
        index_digest="$(jq -er '.index_digest' <<<"${source_json}")"
        dockerfile_reference="${reference}"
        if [[ "${dockerfile_reference}" == docker.io/library/* ]]; then
          dockerfile_reference="${dockerfile_reference#docker.io/library/}"
        elif [[ "${dockerfile_reference}" == docker.io/* ]]; then
          dockerfile_reference="${dockerfile_reference#docker.io/}"
        fi
        grep -Fq "${dockerfile_reference}@${index_digest}" "${dockerfile_path}" \
          || grep -Fq "${reference}@${index_digest}" "${dockerfile_path}" \
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
  local actual_digest source_json source_ref dockerfile context
  local context_path dockerfile_path entry

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
      context_path="$(build_context_path "${image_name}")"
      dockerfile_path="$(build_dockerfile_path "${image_name}" "${context_path}")"
      docker buildx build \
        --platform "${platform}" \
        --file "${dockerfile_path}" \
        --tag "${target}" \
        --push \
        --provenance=false \
        --sbom=false \
        --metadata-file "${metadata_file}" \
        "${context_path}"
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

promote_images() {
  require_command jq
  require_command aws

  local environment="${FLOWFORM_ENVIRONMENT:-staging}"
  local manifest="${RELEASE_MANIFEST_PATH}"
  [[ -f "${manifest}" ]] \
    || die "release manifest not found: ${manifest} (publish first, or set RELEASE_MANIFEST_PATH)"
  [[ -f "${HOST_CONTRACT}" ]] \
    || die "runtime host contract not found: ${HOST_CONTRACT}"
  [[ "${environment}" =~ ^(dev|staging|prod)$ ]] \
    || die "FLOWFORM_ENVIRONMENT must be dev, staging, or prod"

  jq -e '.schema_version == 1' "${manifest}" >/dev/null \
    || die "unsupported release manifest schema: ${manifest}"
  jq -e '.schema_version == 1' "${HOST_CONTRACT}" >/dev/null \
    || die "unsupported runtime host contract: ${HOST_CONTRACT}"

  local commit_sha region
  commit_sha="$(jq -er '.commit_sha' "${manifest}")" \
    || die "release manifest has no commit_sha"
  [[ "${commit_sha}" =~ ^[0-9a-f]{40}$ ]] \
    || die "release manifest commit_sha must be a lowercase 40-character commit SHA"
  region="$(jq -er '.aws.region' "${manifest}")" \
    || die "release manifest has no AWS region"

  printf 'Promoting release %s into the %s role manifests.\n' "${commit_sha}" "${environment}"

  local image_name target digest target_digest repository reference entry
  local normalized_images='{}'
  while IFS= read -r entry; do
    image_name="$(jq -er '.name' <<<"${entry}")"
    target="$(jq -er '.target' <<<"${entry}")"
    digest="$(jq -er '.digest' <<<"${entry}")"

    [[ "${digest}" =~ ^sha256:[0-9a-f]{64}$ ]] \
      || die "${image_name} has an invalid digest in the release manifest"

    # Publication records a digest-qualified target. Accept the older
    # tag-qualified form as well, but always normalize to one repository
    # followed by exactly one verified digest.
    if [[ "${target}" == *@sha256:* ]]; then
      repository="${target%@sha256:*}"
      target_digest="sha256:${target##*@sha256:}"
      [[ "${target_digest}" == "${digest}" ]] \
        || die "${image_name} target digest does not match its digest field"
    else
      repository="${target%:*}"
    fi
    [[ -n "${repository}" && "${repository}" != "${target}" ]] \
      || die "${image_name} target is not tag- or digest-qualified"
    reference="${repository}@${digest}"
    normalized_images="$(
      jq --arg name "${image_name}" --arg reference "${reference}" \
        '. + {($name): $reference}' <<<"${normalized_images}"
    )"
  done < <(jq -c '.images[]' "${manifest}")

  local role parameter_template parameter value
  for role in app proxy; do
    parameter_template="$(
      jq -er --arg role "${role}" '.roles[$role].release_parameter' "${HOST_CONTRACT}"
    )" || die "runtime host contract has no release parameter for ${role}"
    parameter="${parameter_template//\{environment\}/${environment}}"

    if [[ "${role}" == "app" ]]; then
      value="$(
        jq -cn \
          --arg source_commit "${commit_sha}" \
          --arg backend "$(jq -er '.backend' <<<"${normalized_images}")" \
          --arg alloy "$(jq -er '.alloy' <<<"${normalized_images}")" \
          '{
            schema_version: 1,
            source_commit: $source_commit,
            images: {backend: $backend, alloy: $alloy}
          }'
      )"
    else
      value="$(
        jq -cn \
          --arg source_commit "${commit_sha}" \
          --arg caddy "$(jq -er '.caddy' <<<"${normalized_images}")" \
          --arg squid "$(jq -er '.squid' <<<"${normalized_images}")" \
          --arg alloy "$(jq -er '.alloy' <<<"${normalized_images}")" \
          '{
            schema_version: 1,
            source_commit: $source_commit,
            images: {caddy: $caddy, squid: $squid, alloy: $alloy}
          }'
      )"
    fi

    if [[ "${DRY_RUN:-0}" == "1" ]]; then
      printf 'DRY_RUN: would set %s=%s\n' "${parameter}" "${value}"
      continue
    fi
    aws ssm put-parameter \
      --region "${region}" \
      --name "${parameter}" \
      --value "${value}" \
      --type String \
      --overwrite >/dev/null \
      || die "failed to write ${parameter}"
    printf 'set %s\n' "${parameter}"
  done

  printf 'Promotion complete. Each host reads one complete role manifest on its next convergence.\n'
}

case "${1:-}" in
  validate)
    validate_manifest
    ;;
  publish)
    publish_images
    ;;
  promote)
    promote_images
    ;;
  *)
    die "usage: $0 {validate|publish|promote}"
    ;;
esac
