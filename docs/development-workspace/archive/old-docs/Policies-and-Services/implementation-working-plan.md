# Policies and Services Implementation Router

This file is only a router. Do not load the full implementation folder unless a
specific pass instructs you to.

Start here:

1. Read `docs/Policies-and-Services/implementation/README.md`.
2. Read `docs/Policies-and-Services/implementation/agent-operating-rules.md`.
3. Read only the current target file under
   `docs/Policies-and-Services/implementation/targets/`.
4. Read only the policy docs, code files, callers, and tests named by that
   target or by the local context pack.

Hard rule: do not search every file under `docs/Policies-and-Services/implementation`.
Only open the instructed target plus shared operating files.

Tool rule: do not use context-mode search to discover implementation scope. Use
the router and target files. Use context-mode for codebase inspection once the
target pass is known and code context is needed.

Communication rule: use the `caveman` skill when self-reasoning summaries,
implementation explanations, and pass reports are requested, unless the user
turns it off.

Current index:

* `implementation/README.md`
* `implementation/agent-prompts.md`
* `implementation/agent-operating-rules.md`
* `implementation/pass-template.md`
* `implementation/flow-matrix.md`
* `implementation/validation-ladder.md`
* `implementation/targets/01-runtime-inventory.md`
* `implementation/targets/02-access-grant.md`
* `implementation/targets/03-recognition-token-lookup.md`
* `implementation/targets/04-subject-resolution.md`
* `implementation/targets/05-token-action.md`
* `implementation/targets/06-session-start-orchestration.md`
* `implementation/targets/07-transaction-boundary.md`
* `implementation/targets/08-authenticated-account-linking.md`
* `implementation/targets/09-response-cookie-contract.md`
* `implementation/targets/10-flow-matrix-tests.md`
* `implementation/targets/11-stale-modules.md`
* `implementation/targets/12-docstring-cleanup.md`
* `implementation/pass-reports/`
