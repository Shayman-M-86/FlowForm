---
name: commit
description: Stage and commit the current repository changes, resolve actionable pre-commit failures, and retry until the commit succeeds. Use when the user invokes /commit or $commit, or explicitly asks the agent to commit the current work.
---

# Commit

1. Run `git add -A`.
2. Run `git commit -m "<short message based on the current task>"`.
3. Read all command output. If the commit fails, follow the reported
   instructions, run `git add -A`, and retry the commit.
4. Report the successful commit and any fixes made.

Never bypass the pre-commit hook or push.
