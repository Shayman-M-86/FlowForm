#!/usr/bin/env bash
set -Eeuo pipefail
echo '[flowform-image] configuring EC2 defaults'
cloud-init query ds 2>/dev/null || true
if systemctl list-unit-files chronyd.service --no-legend 2>/dev/null | grep -q '^chronyd\.service'; then
  systemctl enable chronyd.service
elif systemctl list-unit-files systemd-timesyncd.service --no-legend 2>/dev/null | grep -q '^systemd-timesyncd\.service'; then
  systemctl enable systemd-timesyncd.service
else
  echo '[flowform-image] no supported time synchronization service found' >&2
  exit 1
fi
