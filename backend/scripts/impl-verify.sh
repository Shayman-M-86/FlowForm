#!/usr/bin/env bash
# impl-verify.sh — extract claims from the latest pass report for quick code review.
# Prints only what the last pass claimed to implement and which files to check.
# No tests, no docs, no tooling context.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
REPORTS_DIR="$REPO_ROOT/docs/Policies-and-Services/implementation/pass-reports"

LATEST=$(ls -1 "$REPORTS_DIR" | sort | tail -1)
REPORT="$REPORTS_DIR/$LATEST"

echo "=== impl-verify: $LATEST ==="
echo ""

echo "--- changed files ---"
awk '/^Changed files:/,/^$/' "$REPORT" | grep '^\*'
echo ""

echo "--- behavior claimed ---"
awk '/^Behavior implemented:/,/^$/' "$REPORT" | grep '^\*'
echo ""

echo "--- verify instructions ---"
echo "Read only the changed files listed above."
echo "For each behavior claim, check whether the code actually does it."
echo "Report: [ok] or [wrong/missing] per claim, one line each."
echo "Do not run tests. Do not read docs. Do not implement anything."
