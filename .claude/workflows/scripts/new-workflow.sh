#!/usr/bin/env bash
# new-workflow.sh — scaffold a new Claude workflow from the template.
# Run from the repo root: bash .claude/workflows/scripts/new-workflow.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKFLOWS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE_DIR="$WORKFLOWS_DIR/_template"

echo ""
echo "=== New Workflow Setup ==="
echo ""

# ---------------------------------------------------------------------------
# Gather inputs
# ---------------------------------------------------------------------------
read -rp "Workflow name (kebab-case, e.g. auth-refactor): " WORKFLOW_SLUG
if [ -z "$WORKFLOW_SLUG" ]; then
  echo "ERROR: Workflow name is required."
  exit 1
fi

WORKFLOW_SLUG=$(echo "$WORKFLOW_SLUG" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd 'a-z0-9-')
WORKFLOW_NAME=$(echo "$WORKFLOW_SLUG" | sed 's/-/ /g' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) tolower(substr($i,2))}1')

DEST="$WORKFLOWS_DIR/$WORKFLOW_SLUG"

if [ -d "$DEST" ]; then
  echo "ERROR: Workflow '$WORKFLOW_SLUG' already exists at $DEST"
  exit 1
fi

read -rp "One-line description: " WORKFLOW_DESCRIPTION
if [ -z "$WORKFLOW_DESCRIPTION" ]; then
  echo "ERROR: Description is required."
  exit 1
fi

read -rp "Number of passes: " NUM_PASSES
if ! [[ "$NUM_PASSES" =~ ^[1-9][0-9]*$ ]]; then
  echo "ERROR: Number of passes must be a positive integer."
  exit 1
fi

echo ""
echo "Enter a name for each pass (kebab-case, e.g. runtime-inventory):"
declare -a PASS_NAMES=()
for i in $(seq 1 "$NUM_PASSES"); do
  read -rp "  Pass $i name: " pass_name
  pass_name=$(echo "$pass_name" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd 'a-z0-9-')
  PASS_NAMES+=("$pass_name")
done

# ---------------------------------------------------------------------------
# Confirm
# ---------------------------------------------------------------------------
echo ""
echo "Creating workflow: $WORKFLOW_SLUG"
echo "  Description: $WORKFLOW_DESCRIPTION"
echo "  Passes:"
for i in $(seq 1 "$NUM_PASSES"); do
  printf "    %02d-%s\n" "$i" "${PASS_NAMES[$((i-1))]}"
done
echo ""
read -rp "Proceed? [y/N] " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
  echo "Aborted."
  exit 0
fi

# ---------------------------------------------------------------------------
# Create directory structure
# ---------------------------------------------------------------------------
mkdir -p "$DEST/source"
mkdir -p "$DEST/working/pass-reports"
mkdir -p "$DEST/working/targets"
mkdir -p "$DEST/scripts"

# Copy and fill in template files
substitute() {
  sed \
    -e "s/{{WORKFLOW_NAME}}/$WORKFLOW_NAME/g" \
    -e "s/{{WORKFLOW_SLUG}}/$WORKFLOW_SLUG/g" \
    -e "s/{{WORKFLOW_DESCRIPTION}}/$WORKFLOW_DESCRIPTION/g" \
    "$1"
}

substitute "$TEMPLATE_DIR/working/AGENT.md"     > "$DEST/working/AGENT.md"
substitute "$TEMPLATE_DIR/working/OPERATOR.md"  > "$DEST/working/OPERATOR.md"
substitute "$TEMPLATE_DIR/working/pass-template.md" > "$DEST/working/pass-template.md"
substitute "$TEMPLATE_DIR/scripts/session-start.sh" > "$DEST/scripts/session-start.sh"
chmod +x "$DEST/scripts/session-start.sh"

# state.md
cat > "$DEST/working/state.md" <<EOF
current_pass: 1
status: in-progress
EOF

# Per-pass target directories
for i in $(seq 1 "$NUM_PASSES"); do
  pass_dir="$DEST/working/targets/$(printf '%02d' "$i")-${PASS_NAMES[$((i-1))]}"
  mkdir -p "$pass_dir"

  cat > "$pass_dir/spec.md" <<EOF
# Pass $(printf '%02d' "$i"): ${PASS_NAMES[$((i-1))]}

## Goal

Describe what this pass must achieve.

## In scope

- ...

## Out of scope

- ...

## Done when

- [ ] Signal 1
- [ ] Tests pass: \`<exact test command>\`

## Dependencies

Prior passes that must be complete before this one: $([ "$i" -eq 1 ] && echo "none" || echo "pass $(printf '%02d' "$((i-1))")")
EOF

  cat > "$pass_dir/prompt.md" <<EOF
Read the spec for this pass at \`working/targets/$(printf '%02d' "$i")-${PASS_NAMES[$((i-1))]}/spec.md\`.

Stop if <dependency not yet implemented>.
Implement only <scope of this pass>.
EOF
done

# Workflow-level README
cat > "$DEST/README.md" <<EOF
# Workflow: $WORKFLOW_NAME

$WORKFLOW_DESCRIPTION

## Passes

$(for i in $(seq 1 "$NUM_PASSES"); do
  printf '%d. %s\n' "$i" "${PASS_NAMES[$((i-1))]}"
done)

## Setup checklist

- [ ] Copy or move source/spec docs into \`source/\`
- [ ] Update \`working/AGENT.md\` — fill in the \`SOURCE_DOCS\` list with paths
      relative to the workflow root (e.g. \`source/core-policies.md\`)
- [ ] Fill in \`working/targets/01-*/spec.md\` for the first pass
- [ ] Fill in \`working/targets/01-*/prompt.md\`
- [ ] Run: \`bash .claude/workflows/$WORKFLOW_SLUG/scripts/session-start.sh\`

See \`working/OPERATOR.md\` for full operating instructions.
EOF

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "Created: $DEST"
echo ""
echo "Next steps:"
echo "  1. Copy your source/spec docs into $DEST/source/"
echo "  2. Edit $DEST/working/AGENT.md — fill in SOURCE_DOCS list"
echo "  3. Edit $DEST/working/targets/ — fill in spec.md and prompt.md per pass"
echo "  4. Start a session: bash $DEST/scripts/session-start.sh"
echo ""
