#!/usr/bin/env bash
set +e

diagnostic_log="/var/log/flowform-packer-boot.log"
touch "${diagnostic_log}"
chmod 0600 "${diagnostic_log}"
exec > >(tee -a "${diagnostic_log}" /dev/console) 2>&1

printf '\n=== FlowForm Packer boot diagnostics: %s ===\n' \
  "$(date --iso-8601=seconds)"

printf '\n--- system identity ---\n'
uname -a
cat /etc/os-release

printf '\n--- network addresses and routes ---\n'
ip -brief address
ip route show

printf '\n--- SSH configuration and listener ---\n'
if command -v sshd >/dev/null 2>&1; then
  sshd -t
  printf 'sshd_config_validation_exit=%s\n' "$?"
else
  printf 'sshd executable is missing\n'
fi
systemctl --no-pager --full status sshd.service
systemctl is-enabled sshd.service
systemctl is-active sshd.service
ss -lntp

printf '\n--- host firewall ---\n'
systemctl --no-pager --full status nftables.service
systemctl is-enabled nftables.service
systemctl is-active nftables.service
if command -v nft >/dev/null 2>&1; then
  nft list ruleset
fi

printf '\n--- cloud-init ---\n'
cloud-init status --long
journalctl --boot --no-pager --output=short-iso \
  --unit=sshd.service \
  --unit=nftables.service \
  --unit=cloud-init.service \
  --unit=cloud-config.service \
  --lines=250

printf '=== FlowForm Packer boot diagnostics complete ===\n\n'
exit 0
