#!/usr/bin/env bash

cmd_prune_main() {
  local platform="${1:-}" environment="" mode="" region cdk_account caller_account
  local images_json image_id role parent creation parameter value state
  local -a candidate_ids=()
  local -a deletion_ids=()
  local -a live_ids=()
  local -A protected=()
  local -A reasons=()

  if [[ "${platform}" == -h || "${platform}" == --help ]]; then
    printf '%s\n' \
      'Usage: image prune aws --environment <dev|staging|prod> <--dry-run|--apply>'
    return
  fi
  [[ $# -gt 0 ]] && shift || true
  [[ "${platform}" == aws ]] \
    || die "usage: image prune aws --environment <dev|staging|prod> <--dry-run|--apply>"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --environment)
        [[ $# -ge 2 ]] || die "--environment requires a value"
        environment="$2"
        shift 2
        ;;
      --dry-run|--apply)
        [[ -z "${mode}" ]] || die "choose exactly one of --dry-run or --apply"
        mode="$1"
        shift
        ;;
      -h|--help)
        printf '%s\n' \
          'Usage: image prune aws --environment <dev|staging|prod> <--dry-run|--apply>'
        return
        ;;
      *) die "unknown prune argument: $1" ;;
    esac
  done

  [[ "${environment}" =~ ^(dev|staging|prod)$ ]] \
    || die "--environment must be dev, staging, or prod"
  [[ -n "${mode}" ]] || die "choose exactly one of --dry-run or --apply"

  phase "inventory protected AWS AMIs"
  image_aws_session_preflight
  require_command jq
  region="$(image_cdk_region)"
  cdk_account="$(image_cdk_account)"
  caller_account="$(
    aws sts get-caller-identity \
      --profile "${AWS_PROFILE}" \
      --query Account \
      --output text \
      --no-cli-pager
  )"
  [[ "${caller_account}" == "${cdk_account}" ]] \
    || die "AWS profile ${AWS_PROFILE} targets account ${caller_account}, but CDK owns account ${cdk_account}; refusing to prune"

  protect() { # ami-id reason
    local protected_id="$1" reason="$2"
    [[ "${protected_id}" =~ ^ami-[0-9a-f]+$ ]] || return 0
    protected["${protected_id}"]=1
    if [[ -n "${reasons[${protected_id}]:-}" ]]; then
      reasons["${protected_id}"]+=", ${reason}"
    else
      reasons["${protected_id}"]="${reason}"
    fi
  }

  # Protect every environment reference, not only the requested environment:
  # AMIs are account/region artifacts and may be shared across promotions.
  for state in dev staging prod; do
    for role in app proxy base; do
      parameter="$(image_cdk_ami_parameter "${state}" "${role}")"
      if value="$(
        aws ssm get-parameter \
          --profile "${AWS_PROFILE}" \
          --region "${region}" \
          --name "${parameter}" \
          --query Parameter.Value \
          --output text \
          --no-cli-pager 2>/dev/null
      )"; then
        protect "${value}" "SSM ${parameter}"
      fi
    done
  done

  while IFS= read -r image_id; do
    [[ -n "${image_id}" ]] || continue
    live_ids+=("${image_id}")
    protect "${image_id}" "non-terminated EC2 instance"
  done < <(
    aws ec2 describe-instances \
      --profile "${AWS_PROFILE}" \
      --region "${region}" \
      --filters \
        "Name=instance-state-name,Values=pending,running,stopping,stopped,shutting-down" \
      --query 'Reservations[].Instances[].ImageId' \
      --output text \
      --no-cli-pager \
      | tr '\t' '\n'
  )

  images_json="$(
    aws ec2 describe-images \
      --profile "${AWS_PROFILE}" \
      --region "${region}" \
      --owners self \
      --filters \
        "Name=state,Values=available" \
        "Name=tag:project,Values=flowform" \
        "Name=tag:managed_by,Values=packer" \
      --output json \
      --no-cli-pager
  )"

  while IFS= read -r image_id; do
    [[ -n "${image_id}" ]] && candidate_ids+=("${image_id}")
  done < <(jq -r '.Images[]?.ImageId' <<<"${images_json}")

  # Keep the two newest successful child images for each role. Published and
  # live AMIs above remain protected even when they are older.
  for role in app proxy; do
    while IFS= read -r image_id; do
      [[ -n "${image_id}" ]] || continue
      protect "${image_id}" "current/previous ${role} build"
    done < <(
      jq -r --arg role "${role}" '
        [
          .Images[]
          | select(any(.Tags[]?; .Key == "image_role" and .Value == $role))
        ]
        | sort_by(.CreationDate)
        | reverse
        | .[:2]
        | .[].ImageId
      ' <<<"${images_json}"
    )
  done

  # Every protected child retains its exact base parent.
  for image_id in "${!protected[@]}"; do
    parent="$(
      jq -r --arg image_id "${image_id}" '
        .Images[]
        | select(.ImageId == $image_id)
        | [.Tags[]? | select(.Key == "parent_ami_id") | .Value]
        | first // empty
      ' <<<"${images_json}"
    )"
    [[ -n "${parent}" ]] && protect "${parent}" "parent of protected ${image_id}"
  done

  for image_id in "${candidate_ids[@]}"; do
    if [[ -n "${protected[${image_id}]:-}" ]]; then
      log "protect ${image_id}: ${reasons[${image_id}]}"
    else
      deletion_ids+=("${image_id}")
    fi
  done

  if (( ${#deletion_ids[@]} == 0 )); then
    success "no unprotected FlowForm AMIs are eligible for pruning in ${region}"
    return
  fi

  phase "$([[ "${mode}" == "--dry-run" ]] && printf 'preview' || printf 'apply') AWS AMI pruning"
  for image_id in "${deletion_ids[@]}"; do
    role="$(
      jq -r --arg image_id "${image_id}" '
        .Images[]
        | select(.ImageId == $image_id)
        | [.Tags[]? | select(.Key == "image_role") | .Value]
        | first // "unknown"
      ' <<<"${images_json}"
    )"
    creation="$(
      jq -r --arg image_id "${image_id}" \
        '.Images[] | select(.ImageId == $image_id) | .CreationDate' \
        <<<"${images_json}"
    )"
    if [[ "${mode}" == "--dry-run" ]]; then
      log "would deregister ${image_id} role=${role} created=${creation} and delete unshared associated snapshots"
      continue
    fi
    log "deregistering ${image_id} role=${role} created=${creation}"
    aws ec2 deregister-image \
      --profile "${AWS_PROFILE}" \
      --region "${region}" \
      --image-id "${image_id}" \
      --delete-associated-snapshots \
      --no-cli-pager >/dev/null
  done

  if [[ "${mode}" == "--dry-run" ]]; then
    success "dry run complete; ${#deletion_ids[@]} AMI(s) are eligible and no AWS resource was changed"
  else
    success "pruned ${#deletion_ids[@]} unprotected FlowForm AMI(s)"
  fi
}
