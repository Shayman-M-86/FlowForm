#!/usr/bin/env bash
# impl-audit.sh — audit the implementation workflow, not the content.
# Checks structural health: pass coverage, target gaps, file hygiene, script integrity.
# Run via /impl-audit. Do not run as a hook.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
IMPL_DIR="$REPO_ROOT/docs/Policies-and-Services/implementation"
REPORTS_DIR="$IMPL_DIR/pass-reports"
TARGETS_DIR="$IMPL_DIR/targets"

echo "=== impl-audit ==="
echo ""

# 1. Target coverage — which targets have reports, which don't
echo "--- target coverage ---"
for target in "$TARGETS_DIR"/[0-9]*.md; do
  num=$(basename "$target" | grep -oE '^[0-9]+')
  slug=$(basename "$target" .md)
  report=$(ls "$REPORTS_DIR/${num}-"*.md 2>/dev/null | head -1 || true)
  if [ -n "$report" ]; then
    echo "  [done] $slug → $(basename "$report")"
  else
    echo "  [missing] $slug — no report"
  fi
done
echo ""

# 2. Pass report hygiene — check each report has required sections
echo "--- report section hygiene ---"
REQUIRED_SECTIONS=("Changed files" "Behavior implemented" "Tests run" "Trace notes" "Remaining risks" "Next recommended pass")
for report in "$REPORTS_DIR"/[0-9]*.md; do
  name=$(basename "$report")
  missing=()
  for section in "${REQUIRED_SECTIONS[@]}"; do
    if ! grep -q "$section" "$report"; then
      missing+=("$section")
    fi
  done
  if [ ${#missing[@]} -eq 0 ]; then
    echo "  [ok] $name"
  else
    echo "  [incomplete] $name — missing: ${missing[*]}"
  fi
done
echo ""

# 3. Script integrity — check the session-start script references real files
echo "--- session-start script file references ---"
SCRIPT="$REPO_ROOT/backend/scripts/impl-session-start.sh"
grep -oE '\$IMPL_DIR/[^"]+' "$SCRIPT" | sed 's|\$IMPL_DIR/||' | sort -u | while IFS= read -r ref; do
  # Skip dynamic expressions and directory references
  [[ "$ref" == *'$'* || "$ref" == *'*'* ]] && continue
  full="$IMPL_DIR/$ref"
  if [ -f "$full" ] || [ -d "$full" ]; then
    echo "  [ok] $ref"
  else
    echo "  [missing] $ref — not found"
  fi
done
echo ""

# 4. Orphaned files — reports with no matching target
echo "--- orphaned reports (no matching target) ---"
found_any=false
for report in "$REPORTS_DIR"/[0-9]*.md; do
  num=$(basename "$report" | grep -oE '^[0-9]+')
  target=$(ls "$TARGETS_DIR/${num}-"*.md 2>/dev/null | head -1 || true)
  if [ -z "$target" ]; then
    echo "  [orphan] $(basename "$report")"
    found_any=true
  fi
done
if [ "$found_any" = false ]; then
  echo "  (none)"
fi
echo ""

# 5. Agent prompts coverage — check each target has a prompt entry
echo "--- agent prompt coverage ---"
PROMPTS_FILE="$IMPL_DIR/agent-prompts.md"
for target in "$TARGETS_DIR"/[0-9]*.md; do
  num=$(basename "$target" | grep -oE '^[0-9]+')
  padded=$(printf '%02d' "$((10#$num))")
  if grep -q "^## Target ${padded} " "$PROMPTS_FILE"; then
    echo "  [ok] target $padded"
  else
    echo "  [missing] target $padded — no prompt entry"
  fi
done
echo ""

echo "=== audit complete ==="
