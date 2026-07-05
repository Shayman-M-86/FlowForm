#!/usr/bin/env bash
# session-start.sh — boot context for a Session Encryption implementation session.
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

echo "=== Session Encryption session start ==="
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
# Process {{context: <path>}} tokens in prompt.md.
# Each token is replaced inline with the contents of the referenced file.
# Path is resolved relative to the workflow root.
# If a referenced file does not exist the script exits with a clear error.
while IFS= read -r line; do
  if [[ "$line" =~ ^\{\{context:\ *(.+)\}\}$ ]]; then
    ctx_path="${BASH_REMATCH[1]// /}"
    ctx_full="$WORKFLOW_DIR/$ctx_path"
    if [ ! -f "$ctx_full" ]; then
      echo ""
      echo "ERROR: {{context}} injection failed — file not found:"
      echo "  token:    {{context: $ctx_path}}"
      echo "  resolved: $ctx_full"
      echo "  prompt:   $current_target_dir/prompt.md"
      echo ""
      echo "Fix the path in prompt.md or create the missing context file before running again."
      exit 1
    fi
    echo "--- injected: $ctx_path ---"
    cat "$ctx_full"
    echo "--- end: $ctx_path ---"
  else
    echo "$line"
  fi
done < "$current_target_dir/prompt.md"
echo ""

# ---------------------------------------------------------------------------
# 6. Extract pass-forward section from previous report (context carry-over)
# ---------------------------------------------------------------------------
# Only injects the "## Pass-forward" section — not the full report.
# If the agent needs more detail, it can Read the full report manually.
prev_pass=$((current_pass - 1))
if [ "$prev_pass" -ge 1 ]; then
  prev_target_dir=$(find "$TARGETS_DIR" -maxdepth 1 -type d -name "$(printf '%02d' "$prev_pass")-*" | sort | head -1)
  if [ -n "$prev_target_dir" ]; then
    prev_slug=$(basename "$prev_target_dir")
    prev_report="$REPORTS_DIR/$prev_slug.md"
    if [ -f "$prev_report" ]; then
      # Extract from "## Pass-forward" to next "##" heading or EOF
      pass_forward=$(sed -n '/^## Pass-forward/,/^## /{/^## Pass-forward/p;/^## [^P]/!{/^## Pass-forward/!p;}}' "$prev_report")
      if [ -n "$pass_forward" ]; then
        echo "=== PASS-FORWARD FROM: $prev_slug ==="
        echo "(For full report: $REPORTS_DIR/$prev_slug.md)"
        echo "$pass_forward"
        echo ""
      else
        echo "=== PREVIOUS PASS REPORT: $prev_slug ==="
        echo "(No pass-forward section found — injecting full report as fallback)"
        cat "$prev_report"
        echo ""
      fi
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
