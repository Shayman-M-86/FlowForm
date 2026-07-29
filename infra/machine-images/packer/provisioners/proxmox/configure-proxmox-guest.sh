#!/usr/bin/env bash
set -Eeuo pipefail
echo '[flowform-image] configuring Proxmox guest defaults'
sed -i 's/^#\?GRUB_CMDLINE_LINUX=.*/GRUB_CMDLINE_LINUX="console=ttyS0"/' /etc/default/grub || true
if command -v update-grub >/dev/null 2>&1; then
  update-grub
elif command -v grub2-mkconfig >/dev/null 2>&1; then
  grub2-mkconfig -o /boot/grub2/grub.cfg
fi
