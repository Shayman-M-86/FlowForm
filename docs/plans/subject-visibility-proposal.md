# Proposal: Subject & Participant Management for Studio Admins

## The Problem

Admins can manage **participants** (pre-registered subjects) but have no
visibility into the broader **subject** population. Anyone who arrives via a
public or general link creates a subject automatically, but there is no way to:

- See how many subjects exist in a project
- View a subject's identities or participant status
- Distinguish anonymous walk-ins from pre-registered participants
- Update a subject's code or details

---

## Background: Subject vs Participant

| Aspect | Subject | Participant |
|--------|---------|-------------|
| Creation | Auto-created on survey access, or created as part of participant registration | Created by an admin — always references a subject + identity |
| Table | `project_subjects` | `project_participants` |
| Identity | Can have multiple identities (email, authenticated user) and recognition tokens | Enrolled under one specific identity |
| API exposure | **None (internal only)** | Full CRUD via `.../participants` |
| Relationship | Superset — every participant is a subject | Subset — not all subjects are participants |

---

## What Already Exists

### Participant endpoints (fully implemented)

| Method | Path | Operation |
|--------|------|-----------|
| `GET` | `.../participants` | List participants in a project |
| `POST` | `.../participants` | Create a participant (creates subject + identity + participant) |
| `PATCH` | `.../participants/{participant_id}` | Update participant |
| `DELETE` | `.../participants/{participant_id}` | Delete participant |

All paths are under `/api/v1/studio/projects/{project_id}`.

### Subject repository (internal, no API)

| Function | Purpose |
|----------|---------|
| `get_subject()` | Fetch by project + subject_id |
| `create_subject()` | Create with optional subject_code |
| `set_subject_code()` | Update subject_code |
| `set_canonical_subject()` | Mark as alias of another subject |
| `delete_subject()` | Delete a subject |

Missing: `list_subjects()` — subjects can only be fetched by ID today.

---

## Proposed Endpoints

All paths under `/api/v1/studio/projects/{project_id}`.

### Subjects — CRUD

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `.../subjects` | List all subjects in the project. Filterable by `?is_participant=true\|false`, `?search=<subject_code>`, `?has_identity=true\|false`. Returns: id, subject_code, created_at, identity_count, is_participant. |
| `GET` | `.../subjects/{subject_id}` | Subject detail: id, subject_code, identities (type + email if present, no raw tokens), is_participant, canonical/alias status, created_at. |
| `POST` | `.../subjects` | Create a bare subject (no identity, no participant enrollment). Accepts optional `subject_code`. Use case: pre-creating a subject before they arrive. |
| `PATCH` | `.../subjects/{subject_id}` | Update subject_code. |
| `DELETE` | `.../subjects/{subject_id}` | Delete a subject. Cascades to identities and tokens. Fails if subject has linked sessions or is a canonical target of aliases (RESTRICT FK). |

### Subject Identities — Read & Manage

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `.../subjects/{subject_id}/identities` | List identities attached to this subject. Returns: id, identity_type, normalized_email (if present), verification_status, attached_at, revoked_at. |
| `POST` | `.../subjects/{subject_id}/identities` | Attach a new identity (email or authenticated user) to a subject. |
| `DELETE` | `.../subjects/{subject_id}/identities/{identity_id}` | Revoke an identity (sets `revoked_at`; does not hard-delete if the identity is referenced by a participant). |

---

## What This Requires

### Repository layer

- `list_subjects(db, project_id, *, is_participant, search, has_identity)` —
  new query with optional filters. Join to `project_participants` for the
  `is_participant` flag, count identities via subquery.
- `list_subject_identities(db, project_id, subject_id)` — new query.
- `create_identity(db, ...)` / `revoke_identity(db, ...)` — new or extended
  from existing internal helpers.

### Route layer

- New file: `api/v1/studio/projects/subjects.py` mounted on
  `studio_projects_bp`.
- New file: `api/v1/studio/projects/subject_identities.py` (or nested in the
  same file).

### Schema layer

- `SubjectListResponse`, `SubjectDetailResponse` — Pydantic response models.
- `CreateSubjectRequest` (optional `subject_code`).
- `UpdateSubjectRequest` (`subject_code`).
- `SubjectIdentityResponse`, `CreateSubjectIdentityRequest`.

### Permissions

- Reuse `project:manage_members` (same as participants) for write operations.
- Consider a read-only `project:view` or `submission:view` for list/detail if
  you want non-admin roles to see subjects without managing them.

---

## Out of Scope

- **Cross-database concerns** — response enrichment, subject-to-answer views,
  and anything involving the response DB or `AdminResponseService`. Those are
  separate work items that build on top of this.
- **Subject merging API** — the `canonical_subject_id` mechanism exists in the
  model, but exposing merge operations is complex (in-progress sessions,
  recognition tokens). Keep internal for now.
- **Subject anonymization** — compliance feature that needs its own design.
- **Bulk operations** — batch-create participants, CSV export. Nice-to-have
  follow-up.

---

## Implementation Order

1. **Subject list & detail** — `GET .../subjects` and `GET .../subjects/{subject_id}`.
   Highest value: admins can finally see who exists.
2. **Subject create & update** — `POST` and `PATCH`. Low risk, repo functions
   mostly exist already.
3. **Subject delete** — needs careful handling of FK constraints (sessions,
   aliases).
4. **Identity management** — list, attach, revoke. Builds on the subject
   detail view.
