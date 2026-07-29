#!/usr/bin/env bash
# TODO(migration): Update paths, contracts, and runtime wiring for infra-new before this file is used.
set -Eeuo pipefail
echo '[flowform-image] enabling SSM Agent on Amazon Linux'
if ! rpm -q amazon-ssm-agent >/dev/null 2>&1; then
  dnf install -y amazon-ssm-agent || yum install -y amazon-ssm-agent
fi
systemctl enable amazon-ssm-agent.service
