#!/usr/bin/env bash
# Count lines in every tracked/relevant file, excluding caches, node_modules, venvs, etc.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

find "$REPO_ROOT" \
  -type f \
  \( \
    -path "*/.git/*" \
    -o -path "*/node_modules/*" \
    -o -path "*/__pycache__/*" \
    -o -path "*/.venv/*" \
    -o -path "*/venv/*" \
    -o -path "*/.mypy_cache/*" \
    -o -path "*/.pytest_cache/*" \
    -o -path "*/.ruff_cache/*" \
    -o -path "*/dist/*" \
    -o -path "*/build/*" \
    -o -path "*/.next/*" \
    -o -path "*/.turbo/*" \
    -o -path "*/coverage/*" \
    -o -path "*/.cache/*" \
    -o -path "*/htmlcov/*" \
    -o -path "*/logs/*" \
  \) -prune \
  -o -type f \
  ! -iname "*.png" \
  ! -iname "*.jpg" \
  ! -iname "*.jpeg" \
  ! -iname "*.gif" \
  ! -iname "*.webp" \
  ! -iname "*.svg" \
  ! -iname "*.ico" \
  ! -iname "*.bmp" \
  ! -iname "*.tiff" \
  ! -iname "*.avif" \
  ! -iname "*.woff" \
  ! -iname "*.woff2" \
  ! -iname "*.ttf" \
  ! -iname "*.otf" \
  ! -iname "*.eot" \
  ! -iname "*.log" \
  ! -iname "*.lock" \
  ! -iname "*.gen.ts" \
  ! -iname "*.gen.tsx" \
  ! -iname "*.d.ts" \
  ! -iname "*.min.js" \
  ! -iname "*.min.css" \
  ! -iname "*.map" \
  ! -iname "package-lock.json" \
  ! -iname "pnpm-lock.yaml" \
  ! -iname "openapi.yaml" \
  ! -iname "openapi.json" \
  ! -path "*/api/generated/*" \
  ! -iname "*.postman_collection.json" \
  ! -iname "*.postman_environment.json" \
  -print \
| sort \
| while IFS= read -r file; do
    read lines words < <(wc -lw < "$file" 2>/dev/null)
    printf "%7d lines  %8d words  %s\n" "$lines" "$words" "${file#$REPO_ROOT/}"
  done \
| sort -rn \
| tee /tmp/line_counts.txt

TOTAL_LINES=$(awk '{sum += $1} END {print sum}' /tmp/line_counts.txt)
TOTAL_WORDS=$(awk '{sum += $3} END {print sum}' /tmp/line_counts.txt)
FILE_COUNT=$(wc -l < /tmp/line_counts.txt)
echo ""
echo "───────────────────────────────────────"
printf "TOTAL: %d lines  |  %d words  |  %d files\n" "$TOTAL_LINES" "$TOTAL_WORDS" "$FILE_COUNT"
