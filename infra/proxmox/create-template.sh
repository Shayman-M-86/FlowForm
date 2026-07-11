#!/usr/bin/env bash
set -Eeuo pipefail

# Compatibility wrapper: Packer now owns image construction. Run this from a
# checkout with Packer installed; it does not perform cloud-init package baking.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PACKER_DIR="$(cd -- "${SCRIPT_DIR}/../images/packer" && pwd)"
cd "${PACKER_DIR}"
packer init .
packer validate -syntax-only .
packer build -only='proxmox-clone.amazon_linux_2023' .
