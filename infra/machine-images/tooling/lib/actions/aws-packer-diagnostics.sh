#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  printf '%s\n' \
    'Usage: aws-packer-diagnostics.sh REGION SOURCE_COMMIT IMAGE_ROLE REPORT_PATH' \
    '       [FAILURE_REQUEST_PATH FAILURE_COMPLETE_PATH]'
}

[[ $# == 4 || $# == 6 ]] || { usage >&2; exit 2; }
region="$1"
source_commit="$2"
image_role="$3"
report_path="$4"
failure_request_path="${5:-}"
failure_complete_path="${6:-}"
[[ "${image_role}" =~ ^(base|app|proxy)$ ]] || {
  printf 'invalid image role: %s\n' "${image_role}" >&2
  exit 2
}
if [[ -n "${failure_request_path}" ]]; then
  [[ -n "${failure_complete_path}" ]] || {
    printf 'failure snapshot paths must be supplied together\n' >&2
    exit 2
  }
fi

# Keep the complete 0600 report while making the same timestamped diagnostic
# stream visible beside Packer's own output.
exec > >(tee -a "${report_path}") 2>&1

diagnostic_log() {
  if [[ "${FLOWFORM_OPERATION_ID:-}" =~ ^[[:alnum:]][[:alnum:]._-]{0,127}$ ]]; then
    printf '%s | operation_id=%s | %s\n' \
      "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "${FLOWFORM_OPERATION_ID}" "$*"
  else
    printf '%s | %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
  fi
}

instance_id=""
private_ip=""
public_ip=""
instance_profile_arn=""
security_group_id=""
subnet_id=""
vpc_id=""
launch_time=""
record=""
console_fingerprint=""
ssm_online_recorded=0

discover_builder() {
  local state_values="${1:-pending,running}"
  record="$(
    aws ec2 describe-instances \
      --region "${region}" \
      --filters \
        "Name=tag:managed_by,Values=packer" \
        "Name=tag:source_commit,Values=${source_commit}" \
        "Name=tag:image_role,Values=${image_role}" \
        "Name=instance-state-name,Values=${state_values}" \
      --query \
        'sort_by(Reservations[].Instances[], &LaunchTime)[-1].[InstanceId,PrivateIpAddress,PublicIpAddress,IamInstanceProfile.Arn,LaunchTime,SecurityGroups[0].GroupId,SubnetId,VpcId]' \
      --output text 2>/dev/null || true
  )"
  [[ -n "${record}" && "${record}" != None* ]] || return 1
  IFS=$'\t' read -r \
    instance_id private_ip public_ip instance_profile_arn launch_time security_group_id subnet_id vpc_id \
    <<<"${record}"
  [[ -n "${instance_id}" && "${instance_id}" != None ]]
}

capture_ssm_status() {
  [[ -n "${instance_id}" ]] || return 0
  aws ssm describe-instance-information \
    --region "${region}" \
    --filters "Key=InstanceIds,Values=${instance_id}" \
    --query \
      'InstanceInformationList[0].{PingStatus:PingStatus,AgentVersion:AgentVersion,LastPingDateTime:LastPingDateTime,PlatformName:PlatformName,PlatformVersion:PlatformVersion}' \
    --output json 2>&1 || true
}

capture_console_output() {
  [[ -n "${instance_id}" ]] || return 0
  local force="${1:-0}" output fingerprint
  output="$(
    aws ec2 get-console-output \
    --instance-id "${instance_id}" \
    --region "${region}" \
    --latest \
    --query Output \
    --output text 2>&1 || true
  )"
  [[ -n "${output}" && "${output}" != None ]] || return 0
  fingerprint="$(printf '%s' "${output}" | cksum)"
  [[ "${force}" == 1 || "${fingerprint}" != "${console_fingerprint}" ]] || return 0
  console_fingerprint="${fingerprint}"
  diagnostic_log "EC2 serial-console output changed"
  printf '%s\n' "${output}"
}

capture_failure_snapshot() {
  diagnostic_log "capturing final failure snapshot"
  if [[ -z "${instance_id}" ]]; then
    discover_builder \
      'pending,running,stopping,stopped,shutting-down,terminated' || true
  fi
  if [[ -z "${instance_id}" ]]; then
    diagnostic_log "no tagged builder instance was available for the final snapshot"
  else
    diagnostic_log "final builder instance details"
    aws ec2 describe-instances \
      --instance-ids "${instance_id}" \
      --region "${region}" \
      --query \
        'Reservations[0].Instances[0].{InstanceId:InstanceId,State:State,StateReason:StateReason,LaunchTime:LaunchTime,PublicIpAddress:PublicIpAddress,PrivateIpAddress:PrivateIpAddress,SubnetId:SubnetId,VpcId:VpcId,SecurityGroups:SecurityGroups,RootDeviceName:RootDeviceName,BlockDeviceMappings:BlockDeviceMappings}' \
      --output json 2>&1 || true
    diagnostic_log "final EC2 system, instance, and EBS status"
    aws ec2 describe-instance-status \
      --instance-ids "${instance_id}" \
      --include-all-instances \
      --region "${region}" \
      --output json 2>&1 || true
    diagnostic_log "final Systems Manager managed-instance status"
    capture_ssm_status
    diagnostic_log "final Systems Manager connection status"
    aws ssm get-connection-status \
      --target "${instance_id}" \
      --region "${region}" \
      --output json 2>&1 || true
    capture_console_output 1
  fi
  if [[ -n "${failure_complete_path}" ]]; then
    umask 077
    : >"${failure_complete_path}"
    chmod 0600 "${failure_complete_path}"
  fi
  diagnostic_log "final failure snapshot complete"
}

process_failure_request() {
  if [[ -z "${failure_request_path}" || ! -e "${failure_request_path}" ]]; then
    return 0
  fi
  if [[ -n "${failure_complete_path}" && -e "${failure_complete_path}" ]]; then
    return 0
  fi
  capture_failure_snapshot
}

capture_failure_signal() {
  capture_failure_snapshot
}

finish() {
  trap - EXIT INT TERM
  process_failure_request
  capture_console_output
  diagnostic_log "diagnostic monitor stopped"
  exit 0
}
trap finish EXIT INT TERM
trap capture_failure_signal USR1

diagnostic_log \
  "waiting for active Packer builder tagged source_commit=${source_commit} image_role=${image_role}"
for _ in {1..90}; do
  process_failure_request
  if discover_builder; then
    diagnostic_log \
      "builder discovered instance=${instance_id} private_ip=${private_ip} public_ip=${public_ip} instance_profile=${instance_profile_arn} launch=${launch_time} security_group=${security_group_id} subnet=${subnet_id} vpc=${vpc_id}"
    break
  fi
  sleep 2
done

if [[ -z "${instance_id}" ]]; then
  diagnostic_log "no active Packer builder appeared within 180 seconds"
  exit 0
fi

diagnostic_log "effective temporary security-group rules"
aws ec2 describe-security-groups \
  --group-ids "${security_group_id}" \
  --region "${region}" \
  --query 'SecurityGroups[0].{Ingress:IpPermissions,Egress:IpPermissionsEgress}' \
  --output json 2>&1 || true

diagnostic_log "subnet and VPC route tables"
aws ec2 describe-route-tables \
  --region "${region}" \
  --filters "Name=vpc-id,Values=${vpc_id}" \
  --query 'RouteTables[].{Id:RouteTableId,Main:Associations[?Main==`true`].Main,SubnetAssociations:Associations[].SubnetId,Routes:Routes}' \
  --output json 2>&1 || true

diagnostic_log "subnet network ACL"
aws ec2 describe-network-acls \
  --region "${region}" \
  --filters "Name=association.subnet-id,Values=${subnet_id}" \
  --query 'NetworkAcls[].{Id:NetworkAclId,Entries:Entries}' \
  --output json 2>&1 || true

attempt=0
while true; do
  attempt=$((attempt + 1))
  process_failure_request
  status="$(
    aws ec2 describe-instance-status \
      --instance-ids "${instance_id}" \
      --include-all-instances \
      --region "${region}" \
      --query \
        'InstanceStatuses[0].[InstanceState.Name,SystemStatus.Status,InstanceStatus.Status,AttachedEbsStatus.Status]' \
      --output text 2>/dev/null || true
  )"
  diagnostic_log "attempt=${attempt} EC2 state/status=${status:-unavailable}"
  capture_console_output

  ssm_status="$(capture_ssm_status)"
  if [[ -n "${ssm_status}" && "${ssm_status}" != null ]]; then
    diagnostic_log "Systems Manager managed-instance status=${ssm_status}"
    if [[ "${ssm_status}" == *'"PingStatus": "Online"'* ]] && (( ssm_online_recorded == 0 )); then
      diagnostic_log "Session Manager transport is online; no inbound SSH path is used"
      ssm_online_recorded=1
    fi
  else
    diagnostic_log "Systems Manager has not registered the builder yet"
  fi

  sleep 7
done
