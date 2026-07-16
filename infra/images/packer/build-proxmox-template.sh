#!/usr/bin/env bash
set -Eeuo pipefail

# Convenience entry point for the platform-independent Packer image pipeline.
# This script lives inside the consolidated Packer config dir, so packer runs here.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PACKER_DIR="${SCRIPT_DIR}"
cd "${PACKER_DIR}"
packer init .
packer validate -syntax-only .
packer build -only='proxmox-clone.amazon_linux_2023' .
