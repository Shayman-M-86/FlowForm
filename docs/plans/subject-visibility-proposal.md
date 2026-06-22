# Proposal: Subject Visibility for Studio Admins

## The Problem

Today, admins can manage **participants** (pre-registered subjects) but are
completely blind to the broader **subject** population. Anyone who arrives via a
public link creates a subject automatically, but there is no way to:

- See how many subjects exist in a project
- See what a specific subject has done across surveys
- Tell which response belongs to which subject
- Distinguish anonymous walk-ins from pre-registered participants

The response API returns `session_id` but no subject information at all.

---

## Background: Subject vs Participant

| Aspect | Subject | Participant |
|--------|---------|-------------|
| Creation | Auto-created on survey access (public link, general link) or created as part of participant registration | Manually created by an admin via the Studio API |
| Table | `project_subjects` | `project_participants` (always references a subject + identity) |
| Identity | Can have multiple identities (email, authenticated user) and recognition tokens | Enrolled under one specific identity |
| API exposure | None (internal only) | Full CRUD via `/studio/projects/{id}/participants` |
| Relationship | Superset — every participant is a subject | Subset — not all subjects are participants |

---

## What the Architecture Allows (and Doesn't)

The codebase has a deliberate pseudonymity boundary between the core DB and the
response DB. Responses are keyed by a one-way HMAC-derived `session_locator` —
the response DB cannot reverse-lookup a subject. All joins happen in-memory
through `AdminResponseService` + `LocatorService` + AWS Secrets Manager.

This means:

- **We can** enrich any response with subject info by going through the core
  DB's `SubmissionSession.project_subject_id` — the join path already exists in
  `AdminResponseService`.
- **We can** query all sessions for a given subject since `SubmissionSession` has
  a direct FK to `ProjectSubject`.
- **We cannot** query the response DB directly by subject (nor should we — that
  would break the pseudonymity model).

---

## Proposed Endpoints

### Phase 1 — Subject List & Detail

Highest value, lowest risk. Gives admins basic visibility into who exists in
their project.

| Endpoint | Purpose |
|----------|---------|
| `GET .../subjects` | List all subjects in a project. Filterable by `?is_participant=true/false`, `?search=<subject_code>`, `?has_identity=true/false`. Returns subject_code, created_at, identity count, participant flag. |
| `GET .../subjects/{subject_id}` | Subject detail: subject_code, identities (type + email if present, no raw tokens), whether they are a participant, canonical/alias status, created_at. |

**What this requires:**

- A new `list_subjects()` repository function (does not exist yet — subjects are
  only fetched by ID today).
- A new route file under `api/v1/studio/projects/subjects.py`.
- New response schemas.
- Permission checks (reuse project-level read permissions).

---

### Phase 2 — Subject Activity Across Surveys

| Endpoint | Purpose |
|----------|---------|
| `GET .../subjects/{subject_id}/sessions` | List all submission sessions for this subject in the project. Returns survey_id, survey name, session_status (in_progress / completed), started_at, completed_at, last_activity_at. No answer data — just session metadata from the core DB. |

**What this requires:**

- A new repository query joining `SubmissionSession` with `Survey` filtered by
  `project_subject_id`.
- Stays entirely within the core DB — no cross-database work, no crypto.

---

### Phase 3 — Enrich Existing Response Endpoints

| Change | Purpose |
|--------|---------|
| Add `subject_code` and `is_participant` to `SurveyResponseSummaryResponses` | When admins list responses for a survey, they can see which subject submitted each one. |
| Add `subject_code` to `SurveyResponseDetailResponses` | Same for the detail view. |
| Add `?subject_id=` filter to `GET .../surveys/{survey_id}/responses` | Let admins filter responses by subject. |

**What this requires:**

- The `AdminResponseService` already loads sessions from the core DB, so the
  `project_subject_id` is available — it just needs to be carried through to the
  response schema.
- No new cross-DB joins needed.

---

### Phase 4 — Aggregate & Export (Nice-to-Have)

| Endpoint | Purpose |
|----------|---------|
| `GET .../subjects/stats` | Project-level counts: total subjects, participants, subjects with at least one completed session, active sessions. |
| `POST .../subjects/export` | Export subject list with per-survey completion status as CSV. |
| `POST .../participants/bulk` | Batch-create participants from a list of emails. |

---

## Out of Scope

- **Subject anonymization** — compliance feature that needs careful design
  around what happens to linked sessions and response data. Worth doing
  eventually but should not hold up the visibility work.
- **Subject merging API** — the `canonical_subject_id` mechanism exists in the
  model, but exposing merge operations to admins is complex (what happens to
  in-progress sessions? to recognition tokens?). Keep this internal for now.
- **Direct subject-to-answer queries** — anything that would require the
  response DB to know about subjects breaks the pseudonymity design. All
  subject + answer views should go through the existing core-DB-first path.

---

## Suggested Implementation Order

**Phase 1 → Phase 3 → Phase 2 → Phase 4**

Phase 3 (enriching existing responses with `subject_code`) may deliver more
immediate value than Phase 2, since admins are already looking at responses —
they just cannot see who submitted them. Phase 1 is the prerequisite for
everything else.
