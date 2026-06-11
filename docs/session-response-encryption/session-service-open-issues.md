# Session service — open issues and invariant notes

Findings from a path-by-path audit of the three respondent session services:

- `app/services/submissions/access_resolver.py` — `SurveyAccessResolver`
- `app/services/submissions/project_subject_resolver.py` — `ProjectSubjectResolver`
- `app/services/submissions/session_starter.py` — `SessionStarter`

This file records issues that are **deferred** (policy not yet decided) or are
**defensive invariants** that cannot currently be exercised by a test. Bugs that
were fixed outright during the audit are noted at the bottom for context but do
not require follow-up.

Related: [implementation-checklist.md](implementation-checklist.md),
[subject-identity-and-access.md](subject-identity-and-access.md).

---

## Open / deferred

### 1. Dangling subject reference is FK-guaranteed but only defended, not tested

When a link, identity, or recognition token names a `project_subject_id`,
`ProjectSubjectResolver._require_subject` requires that subject to resolve and
raises `SubjectResolutionError` (HTTP 500, server-invariant) on a miss, rather
than silently downgrading a known respondent to an anonymous session.

The composite foreign keys in the core schema make this miss **unreachable
today**:

- `fk_survey_links_assigned_subject_same_project`
- `fk_project_subject_identities_subject_same_project`
- `fk_project_subject_tokens_subject_same_project`

Because the dangling row cannot be constructed without disabling FKs, there is
**no integration test** covering the raise. The guard is intentionally
defensive: it exists so a future schema change (e.g. relaxing a composite FK)
fails loudly instead of mis-attributing a respondent.

**Follow-up:** if FK coverage is ever relaxed, add a focused test that forces the
dangling state and asserts `SubjectResolutionError`.

### 2. Anonymous-subject creation is dead in the live flow

`SessionStarter.start` always calls `ProjectSubjectResolver.resolve` with
`create_anonymous_subject=False`, so the `psr.create_subject(...)` branch is
**unreachable in production**. It is marked with `TODO(subject-policy)` in the
resolver.

This is blocked on the open checklist item: *"Define the product policy for when
anonymous access should create a `project_subjects` row versus leaving
`project_subject_id` null."* Until that policy is decided, the branch stays
present but unused.

**Follow-up:** decide the policy, then either wire `create_anonymous_subject`
through from `SessionStarter` (with a test) or remove the dead branch.

### 3. `project_subject_identities.create_user_identity` always violates a CHECK

`create_user_identity` sets `verification_status='verified'` but leaves
`verified_at=NULL`, which violates
`ck_project_subject_identities_verified_at_consistent`
(`(verification_status = 'verified') = (verified_at IS NOT NULL)`). The helper
would fail at flush for every call.

It currently has **zero production callers**, so the breakage is latent. Tests
that need a verified identity construct the ORM row directly with a valid
`verified_at`.

**Follow-up:** when identity attachment is implemented, either fix the helper to
set `verified_at` (or default to `unverified`) or delete it if a different code
path owns identity creation.

---

## Fixed during the audit (no follow-up needed)

- **Unassigned reusable link crashed session start.** `SessionStarter` called
  `mark_used` for every link; stamping `used_at` on a link with no assignment
  violates `ck_survey_links_used_at_requires_assignment`. Now gated on
  `link.is_single_use`. Covered by
  `test_start_unassigned_reusable_link_session_does_not_stamp_used_at`.
- **Recognition-token side effect ordering.** `mark_used` on the recognition
  token now runs *after* the subject resolves, so a failed resolve does not
  mutate `last_used_at`.
