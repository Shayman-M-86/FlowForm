#!/usr/bin/env bash
# `rehearsal terraform` — direct access to the maintained Terraform root with
# the same Auth0 identifier loading and SSH preflight used by `rehearsal build`.

cmd_terraform_main() {
  if [[ $# -eq 0 || "${1:-}" == -h || "${1:-}" == --help ]]; then
    printf '%s\n' 'Usage: rehearsal terraform <terraform arguments...>' \
      'Examples:' \
      '  rehearsal terraform init' \
      '  rehearsal terraform plan' \
      '  rehearsal terraform apply -auto-approve'
    [[ $# -gt 0 ]] && return 0
    return 2
  fi

  rehearsal_preflight
  # shellcheck source=rehearsal-terraform.sh
  source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/rehearsal-terraform.sh"
  rehearsal_terraform "$@"
}
