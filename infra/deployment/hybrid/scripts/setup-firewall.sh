#!/usr/bin/env bash
set -Eeuo pipefail

# Single-node host policy. Guest firewall configuration belongs to Terraform.
mode=${1:---check}
case "$mode" in
  --check|--apply|--confirm) ;;
  *) echo "Usage: $0 [--check|--apply|--confirm] [admin-ipv4]" >&2; exit 2 ;;
esac
[[ $# -le 2 ]] || exit 2
admin_ip=${2:-192.168.68.106}
admin_ip=$(python3 -c 'import ipaddress, sys; print(ipaddress.IPv4Address(sys.argv[1]))' "$admin_ip")

die() { echo "Error: $*" >&2; exit 1; }
cluster_policy() {
  cat <<'POLICY'
[OPTIONS]
enable: 1
policy_in: DROP
policy_out: ACCEPT
POLICY
}
host_policy() {
  cat <<POLICY
[OPTIONS]
enable: 1

[RULES]
IN ACCEPT -i vmbr0 -source $admin_ip/32 -p tcp -dport 22,8006 # Trusted SSH and web/API administration
IN DROP -p tcp -dport 22,8006,3128,5900:5999,60000:60050 # Override built-in management exceptions
POLICY
}

if [[ $mode == --check ]]; then
  printf '%s\n' '=== Datacenter firewall ==='
  cluster_policy
  printf '\n%s\n' '=== Node firewall ==='
  host_policy
  exit 0
fi

[[ $EUID -eq 0 ]] || die "Run as root on the Proxmox node."
node=$(hostname -s)
cluster_file=/etc/pve/firewall/cluster.fw
host_file=/etc/pve/nodes/$node/host.fw
rollback=flowform-firewall-rollback
lock=/run/lock/flowform-firewall.lock
pending=/run/flowform-firewall.pending
exec 9>"$lock"
flock -n 9 || die "Another host firewall operation is running."

policy_matches() {
  cmp -s "$cluster_file" <(cluster_policy) && cmp -s "$host_file" <(host_policy)
}

[[ -d /etc/pve/firewall && -d /etc/pve/nodes/$node ]] || die "Expected a Proxmox node."
[[ ! -e /etc/pve/corosync.conf ]] || die "This setup is for a standalone node."
[[ -z ${SSH_CONNECTION:-} || ${SSH_CONNECTION%% *} == "$admin_ip" ]] ||
  die "SSH must originate from the chosen admin IP."

if [[ $mode == --confirm ]]; then
  [[ -f $pending ]] || die "No activation is pending."
  systemctl is-active --quiet "$rollback.timer" || die "No rollback timer is active."
  policy_matches || die "Installed policy differs from the expected policy."
  iptables -C INPUT -j PVEFW-INPUT || die "Proxmox IPv4 input chain is not active."
  ip6tables -C INPUT -j PVEFW-INPUT || die "Proxmox IPv6 input chain is not active."
  iptables -C PVEFW-HOST-IN -i vmbr0 -s "$admin_ip/32" -p tcp \
    -m multiport --dports 22,8006 -j RETURN || die "The live admin allow rule is missing."
  for firewall in iptables ip6tables; do
    "$firewall" -C PVEFW-HOST-IN -p tcp -m multiport \
      --dports 22,8006,3128,5900:5999,60000:60050 -j DROP ||
      die "A live management drop rule is missing."
  done
  systemctl stop "$rollback.timer"
  rm -- "$pending"
  echo "Host firewall confirmed. Automatic rollback cancelled."
  exit 0
fi

if [[ -e $cluster_file || -e $host_file ]]; then
  if policy_matches; then
    echo "The requested policy is already installed. Check the rollback timer before closing this session."
    exit 0
  fi
  die "Existing Proxmox firewall configuration requires manual review."
fi
[[ -d /sys/class/net/vmbr0/bridge ]] || die "Expected management bridge vmbr0."
systemctl is-active --quiet pve-firewall || die "Expected the standard pve-firewall service."
if [[ -e $pending ]] || systemctl is-active --quiet "$rollback.timer" ||
  systemctl is-active --quiet "$rollback.service"; then
  die "An earlier activation is awaiting rollback."
fi

# The existing policy files were absent, so rollback restores their absence.
: > "$pending"
# The rollback shell expands its own positional arguments when the timer fires.
# shellcheck disable=SC2016
if ! systemd-run --unit="$rollback" --on-active=5min --timer-property=AccuracySec=1s \
  /usr/bin/flock "$lock" /bin/bash -ec '
    [[ -f $1 ]] || exit 0
    rm -f -- "$2" "$3"
    /usr/sbin/pve-firewall restart
    rm -- "$1"
  ' bash "$pending" "$cluster_file" "$host_file"; then
  rm -- "$pending"
  die "Could not schedule the rollback."
fi

if ! host_policy > "$host_file" || ! cluster_policy > "$cluster_file" ||
  ! pve-firewall compile >/dev/null; then
  flock -u 9
  systemctl start "$rollback.service"
  systemctl stop "$rollback.timer"
  die "Could not compile the host policy. Rollback ran."
fi

printf '%s\n' 'Firewall staged. Verify fresh SSH and web UI access before confirming.' \
  'Run this script with --confirm and the same admin IP within five minutes.'
