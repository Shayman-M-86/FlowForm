#!/usr/bin/env bash
# Proxmox cloud-init snippet helper used by VM lifecycle orchestration.

# proxmox_install_snippet <src_yaml> <snippet_name> [snippet_storage]
# Copies user data into the PVE snippets directory and prints its cicustom ref.
proxmox_install_snippet() {
  local src="$1" name="$2" storage="${3:-local}"
  local dir="/var/lib/vz/snippets"
  [[ -f "${src}" ]] || { echo "proxmox: user-data missing: ${src}" >&2; return 1; }
  pvesm status --content snippets 2>/dev/null | grep -q "^${storage}\\b" \
    || { echo "proxmox: storage '${storage}' has no 'snippets' content - run setup-host.sh" >&2; return 1; }
  install -d -m 0755 "${dir}"
  cp -f "${src}" "${dir}/${name}"
  printf '%s:snippets/%s' "${storage}" "${name}"
}
