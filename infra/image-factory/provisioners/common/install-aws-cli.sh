#!/usr/bin/env bash
set -Eeuo pipefail
. /tmp/flowform-image-lib.sh
aws_version=2.27.41
if command -v aws >/dev/null 2>&1 && aws --version 2>&1 | grep -q "aws-cli/${aws_version} "; then
  log "AWS CLI ${aws_version} already installed"
  exit 0
fi
log "installing checksum-verified AWS CLI ${aws_version}"
case "$(uname -m)" in
  x86_64)
    aws_arch=x86_64
    aws_sha256=15daae6cc803984064e3d4be9cfd07c4ae8ea703633c0a0b67acc6e321f706a3
    ;;
  aarch64|arm64)
    aws_arch=aarch64
    aws_sha256=2c6ed21cf7cff0a7d77118c69bee867128bf4c588db7b5c044ffba5faeb6ccde
    ;;
  *) echo "unsupported arch $(uname -m)" >&2; exit 1 ;;
esac
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-${aws_arch}-${aws_version}.zip" -o "${tmp}/awscliv2.zip"
printf '%s  %s\n' "${aws_sha256}" "${tmp}/awscliv2.zip" | sha256sum --check --status
unzip -q "${tmp}/awscliv2.zip" -d "$tmp"
install_args=()
command -v aws >/dev/null 2>&1 && install_args+=(--update)
"${tmp}/aws/install" "${install_args[@]}"
