#!/usr/bin/env bash
set -Eeuo pipefail

# Run as root on Proxmox after configuring the UniFi trunk for VLANs 30 and 40.
# Preview is the default. Pass --apply to install and activate the two bridges.
case "${1:---check}" in
  --check) apply=false ;;
  --apply) apply=true ;;
  -h|--help)
    echo "Usage: $0 [--check|--apply]"
    exit 0
    ;;
  *) echo "Usage: $0 [--check|--apply]" >&2; exit 2 ;;
esac
[[ $# -le 1 ]] || { echo "Pass only one option." >&2; exit 2; }

die() { echo "Error: $*" >&2; exit 1; }

config=/etc/network/interfaces
[[ $EUID -eq 0 ]] || die "Run this script as root on the Proxmox node."
[[ -e /sys/class/net/nic0 && -d /sys/class/net/vmbr0/bridge ]] ||
  die "Expected the FlowForm uplink nic0 and management bridge vmbr0."
[[ -f $config && ! -L $config ]] || die "Expected a regular file at $config."
[[ ! -e ${config}.new ]] || die "Resolve the pending Proxmox network configuration first."

if $apply; then
  exec 9>/run/lock/flowform-hybrid-network.lock
  flock -n 9 || die "Another hybrid bridge setup is running."
fi

managed_block=$(cat <<'BRIDGES'
# BEGIN FlowForm hybrid bridges
auto vmbr1
iface vmbr1 inet manual
    bridge-ports nic0
    bridge-stp off
    bridge-vlan-aware yes
    bridge-vids 30 40
    pre-up /usr/sbin/sysctl -qw net.ipv6.conf.nic0.disable_ipv6=1
    post-up /usr/sbin/sysctl -qw net.ipv6.conf.vmbr1.disable_ipv6=1
    # FlowForm VM trunk: VLAN 30 ingress and VLAN 40 app via nic0. No host IP.

auto vmbr2
iface vmbr2 inet manual
    bridge-ports none
    bridge-stp off
    post-up /usr/sbin/sysctl -qw net.ipv6.conf.vmbr2.disable_ipv6=1
# FlowForm database network: private bridge with no physical uplink or host IP.
BRIDGES
)

existing_block=$(sed -n '/^# BEGIN FlowForm hybrid bridges$/,/^# \(END FlowForm hybrid bridges$\|FlowForm database network:\)/p' "$config")
if [[ -n $existing_block ]]; then
  if ! diff -q <(sed '/^[[:space:]]*#/d' <<< "$existing_block") \
    <(sed '/^[[:space:]]*#/d' <<< "$managed_block") >/dev/null; then
    die "Review the existing FlowForm bridge block before proceeding."
  fi
else
  configured=$(ifquery --list)
  for bridge in vmbr1 vmbr2; do
    if [[ -e /sys/class/net/$bridge ]] || grep -Fxq "$bridge" <<< "$configured" ||
      ifquery "$bridge" >/dev/null 2>&1; then
      die "$bridge already exists outside the managed block."
    fi
  done
  [[ ! -e /sys/class/net/nic0/master ]] || die "nic0 is already assigned to another interface."
fi

workdir=$(mktemp -d)
trap 'rm -rf -- "$workdir"' EXIT
cp -p -- "$config" "$workdir/original"
cp -p -- "$config" "$workdir/candidate"
if [[ -z $existing_block ]]; then
  printf '\n%s\n' "$managed_block" >> "$workdir/candidate"
fi
ifup --syntax-check --interfaces "$workdir/candidate" vmbr1 vmbr2
if ! $apply; then
  diff -u --label "$config" --label proposed "$workdir/original" "$workdir/candidate" || [[ $? -eq 1 ]]
  exit 0
fi

management_state() {
  ip -o -4 addr show dev vmbr0 | awk '{ print $4 }'
  ip -4 route show default dev vmbr0
}
management_before=$(management_state)
gateway=$(ip -4 route show default dev vmbr0 | awk '$2 == "via" {print $3; exit}')
[[ -n $gateway ]] || die "Expected a default IPv4 gateway on vmbr0."
ping -I vmbr0 -c 1 -W 2 "$gateway" >/dev/null || die "The management gateway did not answer before the change."
if [[ -e ${config}.new ]] || ! cmp -s -- "$config" "$workdir/original"; then
  die "The Proxmox network configuration changed during preflight."
fi

verify_bridges() {
  local iface member vlan
  [[ -e /sys/class/net/vmbr1/brif/nic0 && -d /sys/class/net/vmbr2/bridge ]] || return 1
  [[ $(< /sys/class/net/vmbr1/bridge/vlan_filtering) == 1 ]] || return 1
  for member in /sys/class/net/vmbr2/brif/*; do
    [[ ! -e $member/device ]] || return 1
  done
  for vlan in 30 40; do
    bridge vlan show dev nic0 | awk -v vlan="$vlan" '$NF == vlan { found = 1 } END { exit !found }' || return 1
  done
  for iface in nic0 vmbr1 vmbr2; do
    [[ $(sysctl -n "net.ipv6.conf.$iface.disable_ipv6") == 1 ]] || return 1
    [[ -z $(ip -o addr show dev "$iface") && -z $(ip -6 route show dev "$iface") ]] || return 1
  done
  [[ $(management_state) == "$management_before" ]] &&
    ping -I vmbr0 -c 1 -W 2 "$gateway" >/dev/null
}

if [[ -n $existing_block ]] && verify_bridges; then
  echo "The hybrid bridges are already configured and verified."
  exit 0
fi

if [[ -z $existing_block ]]; then
  backup=$(mktemp /etc/network/interfaces.pre-flowform.XXXXXXXX)
  cp -p -- "$workdir/original" "$backup"
  ipv6_before=$(sysctl -n net.ipv6.conf.nic0.disable_ipv6)
  staged=$(mktemp /etc/network/.flowform-interfaces.XXXXXXXX)
  cp -p -- "$workdir/candidate" "$staged"
  mv -T -- "$staged" "$config"
  echo "Saved the original network configuration at $backup"
fi

if ! ifup --with-depends vmbr1 vmbr2 || ! verify_bridges; then
  if [[ -z $existing_block ]]; then
    ifdown vmbr2 vmbr1 || echo "Check bridge state from the Proxmox console." >&2
    cp -p -- "$backup" "$config"
    sysctl -qw "net.ipv6.conf.nic0.disable_ipv6=$ipv6_before"
  fi
  die "Hybrid bridge activation or verification failed."
fi

ip -br addr show dev vmbr0
bridge vlan show dev nic0
echo "Verified both hybrid bridges and IPv4 reachability to the management gateway."
