# Testing Plan

Focused test coverage for locators, encryption, sessions, revisions,
idempotency, completion, rotation, and failure cases.

Status legend: **Covered**, **Partially covered**, **Not yet implementable**.
For anything not yet implementable, see
[remaining-work-fixed.md](remaining-work-fixed.md) for the phase that unblocks it.

## 37. Test plan

### 37.1 Locator tests  -  not yet implementable

No locator service exists yet (Phase 3 introduces a dev/fake locator service;
Phase 6 introduces the real HMAC-SHA-256 implementation). None of the
"same session/secret produce the same locator", "different linkage versions
produce different locators", etc. checks can be written until then. Keep this
section as the forward-looking plan for Phase 6  -  see
[remaining-work-fixed.md](remaining-work-fixed.md) Phase 6.

### 37.2 Encryption tests  -  not yet implementable

No cipher/DEK provider exists yet. Round-trip, fresh-nonce, tamper-detection,
and nonce-reuse-rejection checks all depend on Phase 6 real cryptography (or
at minimum the Phase 3 dev cipher for shape-level tests). See
[remaining-work-fixed.md](remaining-work-fixed.md) Phase 6.

### 37.3 Session-start tests  -  covered (core resolution); envelope items remain

`backend/tests/integration/core/test_submission_session_starter.py` covers:

* valid public-slug access starts a session and binds the published survey
  version (`test_start_public_slug_session_creates_anonymous_core_session`)
* valid assigned-link access starts a session, attaches the link's assigned
  participant's `project_subject_id`, and stamps the link `used_at`
  (`test_start_assigned_link_session_uses_server_owned_subject`)
* an unassigned reusable link starts a session without stamping `used_at`,
  honoring `ck_survey_links_used_at_requires_assignment`
  (`test_start_unassigned_reusable_link_session_does_not_stamp_used_at`)
* the session binds to exactly one survey version
* `submission_sessions.project_subject_id` is set when a subject resolves and
  left null for anonymous sessions
* only the browser session token *hash* is persisted
  (`hash_browser_session_token` comparison)

Expired/inactive link rejection is covered at the access-resolver layer (see
37.4 below), which `SessionStarter` depends on.

**Remaining  -  see [remaining-work-fixed.md](remaining-work-fixed.md) Phase 3:**

* a response envelope is created during session start
* only a token hash reaches the core database *and* the raw browser token is
  returned only after both the core and response stores succeed (currently
  there's only one store, so this can't be tested end-to-end yet)
* an envelope-creation failure does not expose a broken session

### 37.4 Subject access tests  -  covered for v1 policy

`backend/tests/integration/core/test_project_subject_resolver.py` covers:

* assigned-link resolution takes priority and resolves to the link's assigned
  participant's subject (`test_resolve_prefers_link_assigned_participant`)
* authenticated-user resolution via a verified `project_subject_identities`
  row (`test_resolve_uses_actor_active_user_identity`)
* an authenticated actor with no identity row resolves to `source == "none"`
  (`test_resolve_ignores_actor_without_identity`)
* recognition-token resolution and `last_used_at` stamping
  (`test_resolve_uses_recognition_token_and_marks_used`)
* revoked recognition tokens are ignored
  (`test_resolve_ignores_revoked_recognition_token`)
* no-context resolution returns `source == "none"`, subject `None`
  (`test_resolve_returns_none_when_no_context_matches`)
* anonymous-subject creation *when explicitly requested*
  (`test_resolve_creates_anonymous_subject_when_requested`)  -  this exercises
  the resolver's `create_anonymous_subject=True` path directly; it is not used
  by `SessionStarter` under the conservative v1 policy
* `project_subject_identities.create_user_identity` stores the authenticated
  user's normalized email, `verified_at`, and matching verified status

`backend/tests/integration/core/test_survey_access_resolver.py` covers
link/slug resolution that subject access depends on:

* public-slug resolution returns the published version
  (`test_resolve_public_slug_returns_published_version`)
* unknown slug raises `SurveyNotFoundBySlugError`
* public survey without a published version raises `SurveyNotPublishedError`
* unknown link token raises `LinkNotFoundError`
* inactive link raises `LinkInactiveError`
  (`test_resolve_link_token_inactive_link_raises`)

**Remaining:**

* **anonymous-subject creation by policy**  -  decided for v1: `SessionStarter`
  keeps `create_anonymous_subject=False`, so anonymous public/general-link
  sessions keep `project_subject_id` null
* assigned-email links requiring a matching authenticated identity  -  no test
  found; identity-attachment is not yet implemented
* identity attachment conflicts / revocation-without-deleting-history /
  cross-project reference rejection / `subject_ip_observations`
  retention  -  no dedicated runtime tests found; IP observations are
  schema-only in v1, and cross-project FK rejection is largely enforced by the
  schema rather than exercised by an integration test
* expired link access  -  `LinkInactiveError` is covered for `is_active=False`;
  an explicit expiry-based rejection test was not found

### 37.5 Answer-revision tests  -  not yet implementable

Depends on the response-answer/revision repositories and the answer-save
service (Phase 4). See [remaining-work-fixed.md](remaining-work-fixed.md) Phase 4.

### 37.6 Idempotency tests  -  not yet implementable

Depends on `client_mutation_id` handling in the answer-save service
(Phase 4). See [remaining-work-fixed.md](remaining-work-fixed.md) Phase 4.

### 37.7 Completion tests  -  not yet implementable

Depends on the completion service (Phase 5). See
[remaining-work-fixed.md](remaining-work-fixed.md) Phase 5.

### 37.8 Rotation tests  -  not yet implementable

Depends on real linkage-secret and DEK/KMS key versioning (Phase 6). See
[remaining-work-fixed.md](remaining-work-fixed.md) Phase 6.

### 37.9 Failure tests  -  not yet implementable

Depends on the response envelope/answer write paths and reconciliation tasks
(Phases 3-4 for the envelope/answer paths; Phase 9 for reconciliation and
cached-secret/DEK outage handling). See
[remaining-work-fixed.md](remaining-work-fixed.md) Phases 3-4 and 9.

## Peripheral but relevant coverage

These test files don't map to a single numbered section above but cover
adjacent contract/validation behavior that the session flow depends on:

* `backend/tests/integration/core/test_survey_public_links.py`  -  survey
  public-link resolution
* `backend/tests/unit/test_public_link_validation.py`  -  public-link
  validation rules
* `backend/tests/unit/test_submission_session_contracts.py`  -  pins the
  Phase 2 placeholder response shapes/cookies for the public session routes,
  so Phase 3+ work has a contract to preserve or deliberately change

---
