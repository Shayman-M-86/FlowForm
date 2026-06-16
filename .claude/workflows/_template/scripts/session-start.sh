#!/usr/bin/env bash
# session-start.sh — boot context for a {{WORKFLOW_NAME}} implementation session.
# Run via the impl-start command at the top of a session.
# Do NOT use context-mode or ctx_batch_execute to run this — output must be read inline.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKFLOW_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKING_DIR="$WORKFLOW_DIR/working"
SOURCE_DIR="$WORKFLOW_DIR/source"
TARGETS_DIR="$WORKING_DIR/targets"
REPORTS_DIR="$WORKING_DIR/pass-reports"
STATE_FILE="$WORKING_DIR/state.md"

# ---------------------------------------------------------------------------
# 1. Read state
# ---------------------------------------------------------------------------
current_pass=$(grep '^current_pass:' "$STATE_FILE" | awk '{print $2}')
status=$(grep '^status:' "$STATE_FILE" | awk '{print $2}')

echo "=== {{WORKFLOW_NAME}} session start ==="
echo ""
echo "State: pass $current_pass — $status"
echo ""

# ---------------------------------------------------------------------------
# 2. Detect whether current pass is done (report exists) and auto-advance
# ---------------------------------------------------------------------------
# Find the target directory for the current pass number
current_target_dir=$(find "$TARGETS_DIR" -maxdepth 1 -type d -name "$(printf '%02d' "$current_pass")-*" | sort | head -1)

if [ -z "$current_target_dir" ]; then
  echo "ERROR: No target directory found for pass $current_pass."
  echo "Create $TARGETS_DIR/$(printf '%02d' "$current_pass")-<name>/ with spec.md and prompt.md."
  exit 1
fi

current_slug=$(basename "$current_target_dir")
report_file="$REPORTS_DIR/$current_slug.md"

# If report exists and status is in-progress, auto-advance to next pass
if [ -f "$report_file" ] && [ "$status" = "in-progress" ]; then
  echo "Pass $current_pass report found. Marking done and advancing."
  echo ""
  next_pass=$((current_pass + 1))

  # Check if next target exists
  next_target_dir=$(find "$TARGETS_DIR" -maxdepth 1 -type d -name "$(printf '%02d' "$next_pass")-*" | sort | head -1)

  if [ -z "$next_target_dir" ]; then
    # Update state to done — no next pass
    printf 'current_pass: %s\nstatus: done\n' "$current_pass" > "$STATE_FILE"
    echo "All passes complete. Workflow is done."
    exit 0
  fi

  # Advance state
  printf 'current_pass: %s\nstatus: in-progress\n' "$next_pass" > "$STATE_FILE"
  current_pass=$next_pass
  current_target_dir=$next_target_dir
  current_slug=$(basename "$current_target_dir")
  report_file="$REPORTS_DIR/$current_slug.md"
fi

echo "--- current target: $current_slug ---"
echo ""

# ---------------------------------------------------------------------------
# 3. Print AGENT.md (operating rules + context-mode ban)
# ---------------------------------------------------------------------------
echo "=== AGENT RULES (working/AGENT.md) ==="
cat "$WORKING_DIR/AGENT.md"
echo ""

# ---------------------------------------------------------------------------
# 4. Print source docs inline
# ---------------------------------------------------------------------------
# SOURCE_DOCS are listed in AGENT.md between SOURCE_DOCS: and the next ---
# Parse them out and print each file.
in_source_block=0
while IFS= read -r line; do
  if [[ "$line" == "**SOURCE_DOCS:**" ]]; then
    in_source_block=1
    continue
  fi
  if [ "$in_source_block" = "1" ] && [[ "$line" == "---" ]]; then
    break
  fi
  if [ "$in_source_block" = "1" ] && [[ "$line" =~ ^[[:space:]]*[^[:space:]] ]]; then
    # Strip leading whitespace and markdown list markers
    doc_path=$(echo "$line" | sed 's/^[[:space:]]*[-*] *//' | tr -d '`')
    # Resolve relative to workflow root
    full_path="$WORKFLOW_DIR/$doc_path"
    if [ -f "$full_path" ]; then
      echo "=== SOURCE: $doc_path ==="
      cat "$full_path"
      echo ""
    else
      echo "WARNING: source doc not found: $full_path"
      echo ""
    fi
  fi
done < "$WORKING_DIR/AGENT.md"

# ---------------------------------------------------------------------------
# 5. Print current pass spec and prompt
# ---------------------------------------------------------------------------
echo "=== PASS SPEC: $current_slug/spec.md ==="
cat "$current_target_dir/spec.md"
echo ""

echo "=== PASS PROMPT ==="
cat "$current_target_dir/prompt.md"
echo ""

# ---------------------------------------------------------------------------
# 6. Show previous pass report if it exists (context carry-over)
# ---------------------------------------------------------------------------
prev_pass=$((current_pass - 1))
if [ "$prev_pass" -ge 1 ]; then
  prev_target_dir=$(find "$TARGETS_DIR" -maxdepth 1 -type d -name "$(printf '%02d' "$prev_pass")-*" | sort | head -1)
  if [ -n "$prev_target_dir" ]; then
    prev_slug=$(basename "$prev_target_dir")
    prev_report="$REPORTS_DIR/$prev_slug.md"
    if [ -f "$prev_report" ]; then
      echo "=== PREVIOUS PASS REPORT: $prev_slug ==="
      cat "$prev_report"
      echo ""
    fi
  fi
fi

# ---------------------------------------------------------------------------
# 7. List all pass reports so far
# ---------------------------------------------------------------------------
echo "--- pass reports ---"
if [ -d "$REPORTS_DIR" ] && ls "$REPORTS_DIR"/*.md >/dev/null 2>&1; then
  ls -1 "$REPORTS_DIR"/*.md | xargs -I{} basename {}
else
  echo "(none yet)"
fi
echo ""

echo "=== ready — begin pass $current_pass ==="
