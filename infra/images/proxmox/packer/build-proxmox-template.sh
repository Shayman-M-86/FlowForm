#!/usr/bin/env bash
set -Eeuo pipefail

# Convenience entry point for the platform-independent Packer image pipeline.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PACKER_DIR="$(cd -- "${SCRIPT_DIR}/packer" && pwd)"
cd "${PACKER_DIR}"
packer init .
packer validate -syntax-only .
packer build -only='proxmox-clone.amazon_linux_2023' .
