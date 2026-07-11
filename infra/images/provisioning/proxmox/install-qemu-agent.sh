#!/usr/bin/env bash
set -Eeuo pipefail
. /tmp/flowform-image-lib.sh
echo '[flowform-image] installing/enabling qemu guest agent on Amazon Linux'
pkg_update
pkg_install qemu-guest-agent
systemctl enable qemu-guest-agent
