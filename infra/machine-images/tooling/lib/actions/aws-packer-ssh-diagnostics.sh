#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  printf 'Usage: aws-packer-ssh-diagnostics.sh REGION SOURCE_COMMIT REPORT_PATH\n'
}

[[ $# == 3 ]] || { usage >&2; exit 2; }
region="$1"
source_commit="$2"
report_path="$3"

exec >>"${report_path}" 2>&1

diagnostic_log() {
  printf '%s | %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

instance_id=""
public_ip=""
security_group_id=""
subnet_id=""
vpc_id=""

capture_console_output() {
  [[ -n "${instance_id}" ]] || return
  diagnostic_log "latest EC2 console output"
  aws ec2 get-console-output \
    --instance-id "${instance_id}" \
    --region "${region}" \
    --latest \
    --query Output \
    --output text 2>&1 || true
}

finish() {
  trap - EXIT INT TERM
  capture_console_output
  diagnostic_log "diagnostic monitor stopped"
  exit 0
}
trap finish EXIT INT TERM

diagnostic_log "waiting for active Packer builder tagged source_commit=${source_commit}"
for _ in {1..90}; do
  record="$(
    aws ec2 describe-instances \
      --region "${region}" \
      --filters \
        "Name=tag:managed_by,Values=packer" \
        "Name=tag:source_commit,Values=${source_commit}" \
        "Name=instance-state-name,Values=pending,running" \
      --query \
        'sort_by(Reservations[].Instances[], &LaunchTime)[-1].[InstanceId,PublicIpAddress,LaunchTime,SecurityGroups[0].GroupId,SubnetId,VpcId]' \
      --output text 2>/dev/null || true
  )"
  if [[ -n "${record}" && "${record}" != None* ]]; then
    IFS=$'\t' read -r \
      instance_id public_ip launch_time security_group_id subnet_id vpc_id \
      <<<"${record}"
    if [[ ! "${public_ip}" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
      sleep 2
      continue
    fi
    diagnostic_log \
      "builder discovered instance=${instance_id} public_ip=${public_ip} launch=${launch_time} security_group=${security_group_id} subnet=${subnet_id} vpc=${vpc_id}"
    break
  fi
  sleep 2
done

if [[ -z "${instance_id}" ]]; then
  diagnostic_log "no active Packer builder appeared within 180 seconds"
  exit 0
fi

diagnostic_log "workstation public IPv4 as observed by AWS"
curl --fail --silent --show-error --max-time 10 https://checkip.amazonaws.com 2>&1 || true

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

for attempt in {1..30}; do
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

  if nc -z -w 5 "${public_ip}" 22 >/dev/null 2>&1; then
    diagnostic_log "TCP/22 reachable from this workstation"
    diagnostic_log "SSH host-key handshake"
    ssh-keyscan -T 5 "${public_ip}" 2>&1 || true
    exit 0
  fi

  diagnostic_log "TCP/22 timed out or was refused from this workstation"
  sleep 10
done

diagnostic_log "TCP/22 remained unavailable for five minutes"
