# Pass Templates

REPORT goes to disk. LOCAL PLAN stays in chat/context only — do NOT write it to the report file.

Save reports under `pass-reports/<target-number>-<target-slug>.md`. Chat summary = one sentence + report path.

## Context Pack Template

```md
## Context pack: <pass name>

Relevant docs:
* <path and section>

Current code:
* <path>

Direct callers:
* <path>

Direct tests:
* <path or missing>

Gap and target contract:
* <what's wrong now> → <what it should do/return>

Risk level:
* <low | medium | high | critical>
```

## Local Plan Template (CHAT ONLY)

```md
## Pass: <name>

Gap: <one-line summary>

Steps:
1. <edit>
2. <edit>
3. <test>

Validation: bash backend/scripts/run-tests.sh --ai -k "<filter>"

STOP IF: <condition>

Done when: <signal>
```

## Pass Report Template (WRITE TO DISK)

```md
## Pass report

Changed files:
* ...

Behavior implemented:
* ...

Tests run:
* <exact command> — <N> passed

Failures or skipped validation:
* ...

Trace notes:
* route entry points touched:
* service methods touched:
* repository helpers touched:
* side effects changed:
* transaction boundary changed or unchanged:
* tests that now describe behavior:

Remaining risks:
* ...

Next recommended pass:
* ...
```
