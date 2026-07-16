#!/usr/bin/env bash
set -Eeuo pipefail
echo '[flowform-image] configuring Proxmox guest defaults'
sed -i 's/^#\?GRUB_CMDLINE_LINUX=.*/GRUB_CMDLINE_LINUX="console=ttyS0"/' /etc/default/grub || true
update-grub || true
