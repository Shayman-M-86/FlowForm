#!/usr/bin/env bash
set -Eeuo pipefail

# Sync the repo docs into the Windows-native Obsidian vault.
#
# Why this exists: Obsidian's file watcher cannot watch files that live on the
# WSL filesystem (it fails with `EISDIR: illegal operation on a directory,
# watch ...`), and a Windows->WSL symlink does not help because the watch still
# lands on the WSL 9P filesystem. So instead of linking, we keep the repo docs
# in WSL (fast git/builds) and copy them into a REAL Windows folder that
# Obsidian watches natively. Run this whenever you want the vault refreshed.
#
# The copy is one-way (repo -> vault) and mirror-style: files deleted from the
# repo are removed from the vault too. The vault's own .obsidian config
# (graph, plugins, appearance) is preserved because it is excluded below and
# lives in the vault ROOT, one level above this docs/ subfolder.
#
# Usage:
#   scripts/docs/sync-obsidian-vault.sh          # sync
#   scripts/docs/sync-obsidian-vault.sh --dry-run # show what would change

REPO_DOCS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../docs" && pwd)"
VAULT_DOCS="${OBSIDIAN_VAULT_DOCS:-/mnt/c/Users/Shayman/Documents/FlowForm-vault/docs}"

DRY_RUN=()
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=(--dry-run --itemize-changes)

if [[ ! -d "$(dirname "$VAULT_DOCS")" ]]; then
  echo "ERROR: vault root $(dirname "$VAULT_DOCS") does not exist." >&2
  echo "Create it (and its .obsidian) first, or set OBSIDIAN_VAULT_DOCS." >&2
  exit 1
fi

mkdir -p "$VAULT_DOCS"

# --delete mirrors deletions; excludes keep Obsidian/OS cruft out of the repo->vault
# copy. Note .obsidian is excluded so the vault's config is never overwritten.
rsync -rt --delete "${DRY_RUN[@]}" \
  --exclude='.obsidian/' \
  --exclude='.git/' \
  --exclude='.DS_Store' \
  "$REPO_DOCS"/ "$VAULT_DOCS"/

if [[ ${#DRY_RUN[@]} -eq 0 ]]; then
  echo "Synced $REPO_DOCS -> $VAULT_DOCS"
fi
