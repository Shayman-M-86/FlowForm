#!/usr/bin/env bash
# impl-session-start.sh — prime context for a Policies and Services implementation session.
# Run via /impl-start at the top of a session. Do not run as a hook.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
IMPL_DIR="$REPO_ROOT/docs/Policies-and-Services/implementation"
REPORTS_DIR="$IMPL_DIR/pass-reports"

echo "=== impl-session-start ==="
echo ""

# 1. Print fixed boot-up files in full
for f in \
  "$IMPL_DIR/HOW-TO-RUN.md" \
  "$IMPL_DIR/README.md" \
  "$IMPL_DIR/agent-operating-rules.md" \
  "$IMPL_DIR/flow-matrix.md"
do
  echo "--- $f ---"
  cat "$f"
  echo ""
done

# 2. List pass reports
echo "--- pass reports ---"
if [ -d "$REPORTS_DIR" ]; then
  ls -1 "$REPORTS_DIR"
else
  echo "(none yet)"
fi
echo ""

# 3. Print latest report and auto-detect next target prompt
if [ -d "$REPORTS_DIR" ]; then
  LATEST=$(ls -1 "$REPORTS_DIR" | sort | tail -1)
  if [ -n "$LATEST" ]; then
    echo "--- latest: $LATEST ---"
    cat "$REPORTS_DIR/$LATEST"
    echo ""

    # Derive next target number from latest report filename (e.g. 05-token-action.md -> 06)
    LATEST_NUM=$(echo "$LATEST" | grep -oE '^[0-9]+' | sed 's/^0*//')
    NEXT_NUM=$((LATEST_NUM + 1))
    NEXT_PADDED=$(printf '%02d' "$NEXT_NUM")

    # Print the next target file
    TARGET_FILE=$(ls "$IMPL_DIR/targets/${NEXT_PADDED}-"*.md 2>/dev/null | head -1)
    if [ -n "$TARGET_FILE" ]; then
      echo "--- next target: $TARGET_FILE ---"
      cat "$TARGET_FILE"
      echo ""
    else
      echo "--- next target: ${NEXT_PADDED} (no target file found — all targets complete?) ---"
    fi

    # Find and print the matching prompt from agent-prompts.md
    PROMPTS_FILE="$IMPL_DIR/agent-prompts.md"
    if [ -f "$PROMPTS_FILE" ]; then
      PROMPT=$(awk "/^## Target ${NEXT_PADDED} /,/^---$/" "$PROMPTS_FILE" | head -n -1)
      if [ -n "$PROMPT" ]; then
        echo "--- next target prompt ---"
        echo "$PROMPT"
      else
        echo "--- next target: ${NEXT_PADDED} (no prompt found — all targets complete?) ---"
      fi
    fi
  fi
fi
