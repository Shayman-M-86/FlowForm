---
title: Environment variables
document_type: reference
status: scaffold
authority: canonical
verified_against_commit: null
tags: [configuration]
related_code:
  - "../../backend/app/core/config.py"
  - "../../infra/deployment/bootstrap/"
related_docs:
  - "Configuration catalogue"
  - "Secrets and configuration"
  - "Configuration index"
---

# Environment variables
Provides concise verified reference facts for environment variables.

## Reference scope
This section defines which exact facts belong here.
TODO: Verify this against the current implementation.

## Canonical source
Each variable is authoritative in the module or script that reads it; this
catalogue only points there.

- **Backend application settings** — `backend/app/core/config.py` (the settings
  model). See also [[Configuration catalogue]].
- **Boot-time deploy variables** — the header comment blocks of the bootstrap
  scripts under `infra/deployment/bootstrap/`, which list each script's required
  and optional environment. The app bootstrap
  (`infra/deployment/bootstrap/bootstrap-app.sh`) documents, among others:
  - `BACKEND_IMAGE` — overrides the image ref (rehearsal points it at the local registry).
  - `BOOTSTRAP_DRY_RUN=1` — print intended actions, change nothing.
  - `BOOTSTRAP_IMAGE_PULL_MAX_ATTEMPTS` — image-pull retries before failing the boot (default 60).
  - `BOOTSTRAP_IMAGE_PULL_RETRY_DELAY_SECONDS` — delay between those retries (default 5).

  The pull retry lets the app boot wait out an empty rehearsal registry until the
  operator's image push lands; in production the image is already present, so the
  pull succeeds on the first attempt and the retry adds no latency.

## Entries
This section will contain concise searchable entries after verification.
TODO: Verify this against the current implementation.

## Update procedure
This section explains how to refresh entries without adding unverified assumptions.
TODO: Verify this against the current implementation.

## Related documents

- [[Configuration catalogue]]
- [[Secrets and configuration]]
- [[Configuration index]]
