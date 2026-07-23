#!/usr/bin/env bash
set -Eeuo pipefail
. /tmp/flowform-image-lib.sh
if command -v aws >/dev/null 2>&1; then log "AWS CLI already installed"; exit 0; fi
log "installing AWS CLI v2"
case "$(uname -m)" in x86_64) aws_arch=x86_64 ;; aarch64|arm64) aws_arch=aarch64 ;; *) echo "unsupported arch $(uname -m)" >&2; exit 1 ;; esac
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-${aws_arch}.zip" -o "${tmp}/awscliv2.zip"
unzip -q "${tmp}/awscliv2.zip" -d "$tmp"
"${tmp}/aws/install"
