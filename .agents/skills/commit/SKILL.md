---
name: commit
description: Inspect, stage, validate, and commit the current intended FlowForm changes through the repository pre-commit hook. Use when the user invokes /commit or $commit, or explicitly asks the agent to commit the current work and resolve actionable pre-commit failures before reporting the resulting commit.
---

# Commit FlowForm changes

Create one local commit from the current intended work. Treat invocation as
authorization to stage that work, run the real pre-commit hook through
`git commit`, apply safe in-scope repairs requested by the hook, and retry until
the commit succeeds or a material blocker requires the user.

Do not push, amend an existing commit, bypass hooks, or include unrelated work.

## Workflow

1. Inspect `git status --short`, staged and unstaged diffs, and untracked files.
   With no narrower user scope, target all current changes that belong to the
   work being handed off. Exclude obvious editor files, secrets, caches, build
   output, and unrelated pre-existing changes. Ask only when material scope is
   genuinely ambiguous.
2. Review the selected diff for accidental sensitive values and generated files
   that should be produced through an owning generator. Preserve all excluded
   changes in place.
3. Stage exact selected paths with `git add -- <paths>`. Do not use
   `git add -A`, `git add .`, reset, restore, checkout, or stash.
4. Derive a concise imperative commit subject from the staged diff unless the
   user supplied one. Inspect `git diff --cached --check` and
   `git diff --cached --stat`.
5. Confirm `git config --get core.hooksPath` resolves to `.githooks`. Run
   `git commit -m "<subject>"`. Do not run the hook separately as a substitute:
   the commit must exercise `.githooks/pre-commit`.
6. If the commit fails, read the complete hook output and treat its reported
   repair commands as the next workflow step:
   - For OpenAPI drift, run the printed owning generation or synchronization
     command, review the resulting files, and stage only relevant outputs.
   - For `last_edited` failures, run the printed
     `docsys evidence sync-last-edited` repair and stage the affected selected
     documents.
   - For Project Knowledge evidence drift, review that the affected document
     belongs to this commit and remains accurate, then run the printed
     `docsys evidence promote --staged --stage` command for those paths.
     Development Workspace documents are never promoted.
   - For structural documentation errors, fix the reported selected documents
     and rerun the relevant Docsys validation.
   - For another validation failure, make only an in-scope correction supported
     by the output. Do not weaken or skip the check.
7. Review and restage each repair, then retry `git commit` with the same subject.
   Continue while the failures are actionable and progress is being made. Stop
   and ask the user if remediation would include unrelated work, expose or
   invent credentials, change external systems, or require a substantive choice
   not established by the current task.
8. After success, run `git status --short` and inspect the new commit with
   `git log -1 --format='%h %s'`.

## Report

Keep the final response short:

- commit hash and subject;
- what was included;
- repairs made in response to pre-commit;
- confirmation that the pre-commit checks passed;
- any remaining uncommitted paths.

If blocked, report the failing check, completed repairs, current staged state,
and the one decision or external change needed. Never claim a commit succeeded
without a resulting commit hash.
