#!/usr/bin/env bash
# Shared Proxmox helpers used by the runtime clone orchestration.

# tb_install_snippet <src_yaml> <snippet_name> [snippet_storage]
# Copies user data into the PVE snippets directory and prints its cicustom ref.
tb_install_snippet() {
  local src="$1" name="$2" storage="${3:-local}"
  local dir="/var/lib/vz/snippets"
  [[ -f "${src}" ]] || { echo "tb: user-data missing: ${src}" >&2; return 1; }
  pvesm status --content snippets 2>/dev/null | grep -q "^${storage}\b" \
    || { echo "tb: storage '${storage}' has no 'snippets' content - run setup-host.sh" >&2; return 1; }
  install -d -m 0755 "${dir}"
  cp -f "${src}" "${dir}/${name}"
  printf '%s:snippets/%s' "${storage}" "${name}"
}

# Retained for Proxmox workflows that build a template through cloud-init.
tb_wait_stopped() {
  local vmid="$1" timeout="$2" prefix="${3:-tb}"
  local deadline
  deadline=$(( $(date +%s) + timeout ))
  echo "[${prefix}] waiting up to ${timeout}s for the builder to stop"
  while :; do
    [[ "$(qm status "${vmid}" 2>/dev/null | awk '{print $2}')" == "stopped" ]] && {
      echo "[${prefix}] builder stopped"; return 0;
    }
    if (( $(date +%s) >= deadline )); then
      echo "[${prefix}] ERROR: timeout waiting for VM ${vmid} to stop" >&2
      return 1
    fi
    sleep 5
  done
}

tb_finalize_template() {
  local vmid="$1" prefix="${2:-tb}"
  qm set "${vmid}" --delete cicustom >/dev/null 2>&1 || true
  qm set "${vmid}" --delete ipconfig0 >/dev/null 2>&1 || true
  echo "[${prefix}] converting VM ${vmid} to a template"
  qm template "${vmid}"
}
