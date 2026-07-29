#!/usr/bin/env bash

if [[ -n "${_FLOWFORM_RELEASE_MANIFEST_SOURCED:-}" ]]; then return; fi
_FLOWFORM_RELEASE_MANIFEST_SOURCED=1

flowform_load_release_manifest() { # app|proxy
  local role="$1"
  local parameter="${FLOWFORM_PARAMETER_ROOT:?load instance context first}/${role}/release"
  local manifest image_pattern

  image_pattern='^[0-9]{12}[.]dkr[.]ecr[.][a-z0-9-]+[.]amazonaws[.]com/[a-z0-9._/-]+@sha256:[0-9a-f]{64}$'
  manifest="$(aws ssm get-parameter \
    --region "${AWS_REGION}" \
    --name "${parameter}" \
    --query Parameter.Value \
    --output text \
    --no-cli-pager)"

  jq -e --arg role "${role}" --arg image_pattern "${image_pattern}" '
    .schema_version == 1
    and (.source_commit | test("^[0-9a-f]{40}$"))
    and (.images | type == "object")
    and (
      if $role == "app" then
        (.images | keys | sort) == ["alloy", "backend"]
      else
        (.images | keys | sort) == ["alloy", "caddy", "squid"]
      end
    )
    and ([.images[] | test($image_pattern)] | all)
  ' <<<"${manifest}" >/dev/null || {
    printf 'FlowForm %s release manifest is invalid: %s\n' "${role}" "${parameter}" >&2
    return 1
  }

  FLOWFORM_RELEASE_SOURCE_COMMIT="$(jq -r '.source_commit' <<<"${manifest}")"
  ALLOY_IMAGE="$(jq -r '.images.alloy' <<<"${manifest}")"
  export FLOWFORM_RELEASE_SOURCE_COMMIT ALLOY_IMAGE

  if [[ "${role}" == "app" ]]; then
    BACKEND_IMAGE="$(jq -r '.images.backend' <<<"${manifest}")"
    export BACKEND_IMAGE
  else
    CADDY_IMAGE="$(jq -r '.images.caddy' <<<"${manifest}")"
    SQUID_IMAGE="$(jq -r '.images.squid' <<<"${manifest}")"
    export CADDY_IMAGE SQUID_IMAGE
  fi
}
