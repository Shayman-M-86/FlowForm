---
name: flowform-doc-verification
description: Select, lightly check, present, approve, and promote FlowForm Project Knowledge documentation through the staged Docsys evidence workflow. Use when a user asks a coding agent to verify documentation, approve draft Project Knowledge, review whether selected pages match the implementation, or prepare documentation verification metadata before a commit.
---

# Verify FlowForm documentation

Help the person directing the agent choose and approve documentation. Keep the
evidence check deliberately lightweight; this is a review aid, not a broad
audit.

## Boundaries

- Verify only authored Markdown under `docs/project-knowledge/`.
- Never verify Development Workspace. It remains `draft` or `scaffold`.
- Regenerate generated documentation instead of promoting it.
- Do not edit implementation code during verification.
- Do not commit or push unless explicitly asked.

## 1. Let the user choose

If exact paths were not supplied, use Docsys search, task context, freshness, or
impact results to present a short numbered list of likely Project Knowledge
documents. Include title, path, current status, and one-line subject.

Ask the user to choose exact numbers or paths. Do not silently verify every
candidate. Prefer batches of one to three documents.

## 2. Perform a very lightweight check

For each selected document:

1. Read the page and its declared `related_code`, `change_triggers`, and
   `exclusions`.
2. Inspect only the most obvious implementation locations needed to spot-check
   its material claims. Prefer direct source, tests, configuration, schemas, or
   infrastructure named by the page.
3. Run only cheap, directly relevant commands, such as a focused `rg`, a
   targeted existing test, or:

   ```sh
   PYTHONPATH=tools/docs python3 -m docsys freshness
   PYTHONPATH=tools/docs python3 -m docsys validate \
     --docs-root docs --profile project-knowledge
   ```

4. Stop after the obvious evidence supports the main claims or exposes a
   contradiction. Do not turn this into exhaustive architecture, security, or
   correctness validation.

Classify each page as:

- **ready for approval** — no material mismatch found in the lightweight check;
- **needs correction** — a material claim conflicts with obvious evidence;
- **insufficient evidence** — declared evidence is missing or does not support
  a responsible lightweight judgment.

“Ready” means no issue was found within this narrow check, not that every claim
was proven.

## 3. Present the approval packet

Before changing verification status, show the user:

- the exact document title and clickable path;
- its current status and `last_edited`;
- the document body, or the complete proposed diff when edits were needed;
- the material claims spot-checked and the small evidence set used;
- commands run and their outcome;
- contradictions, uncertainty, and the classification above.

Then ask explicitly whether the selected ready documents should be approved for
verification. Do not promote them until the user approves.

## 4. Apply the decision

If correction is requested, edit only the selected documentation, keep
`status: draft` and `verified_evidence_digest: null`, then present the revised
document again.

After explicit approval:

1. Ensure any selected document edits and relevant implementation changes are
   staged. A clean, unchanged selected document may be promoted directly.
2. Run the promotion command with exact paths:

   ```sh
   PYTHONPATH=tools/docs python3 -m docsys evidence promote --staged \
     docs/project-knowledge/path.md
   ```

3. Run:

   ```sh
   PYTHONPATH=tools/docs python3 -m docsys validate \
     --docs-root docs --profile commit
   ```

4. Report the promoted paths, staged metadata changes, and validation result.

Docsys writes the evidence digest and stages the document. The pre-commit hook
maintains `last_edited`, rechecks affected Project Knowledge against the staged
implementation snapshot, and bypasses Development Workspace verification.
