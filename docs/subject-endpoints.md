# Subject & Participant Endpoints

Studio admins can manage **participants** (enrolled subjects with an identity)
and now also view the broader **subject** population — everyone who has
interacted with a project.

All endpoints live under `/api/v1/studio/projects/{project_id}` and require
the `project:manage_members` permission.

## Endpoints

### GET `.../subjects`

Paginated list of subjects in the project.

**Query params** (all optional):

| Param | Type | Default | Notes |
|---|---|---|---|
| `canonical_status` | `canonical` \| `alias` \| `all` | `canonical` | Filter by merge/alias status |
| `is_participant` | `bool` | — | `true` = enrolled only, `false` = non-enrolled only |
| `search` | `string` | — | Matches subject code or active identity email (ILIKE) |
| `page` | `int` | `1` | Page number (1-based) |
| `page_size` | `int` | `20` | Results per page (max 100) |

**Response shape:**

```json
{
  "subjects": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "subject_code": "sub_xxx",
      "canonical_subject_id": null,
      "is_participant": true,
      "participant_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "active_identity_count": 2,
      "created_at": "2026-06-24T12:00:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

### GET `.../subjects/{subject_id}`

Subject detail with read-only active identities.

**Response shape:**

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "subject_code": "sub_xxx",
  "canonical_subject_id": null,
  "is_participant": true,
  "participant_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "identities": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "identity_type": "email",
      "normalized_email": "user@example.com",
      "verification_status": "unverified",
      "attached_at": "2026-06-24T12:00:00Z",
      "revoked_at": null
    }
  ],
  "created_at": "2026-06-24T12:00:00Z"
}
```

### PATCH `.../subjects/{subject_id}`

Update a subject's code.

**Request body:**

```json
{ "subject_code": "new-code" }
```

Returns the same shape as the detail endpoint.

---

## Participant endpoints

Base path: `.../participants`

### GET `.../participants`

Paginated list of participants in the project.

**Query params** (all optional):

| Param | Type | Default | Notes |
|---|---|---|---|
| `search` | `string` | — | Matches subject code or identity email (ILIKE) |
| `page` | `int` | `1` | Page number (1-based) |
| `page_size` | `int` | `20` | Results per page (max 100) |

**Response shape:**

```json
{
  "participants": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "subject_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "subject_code": "sub_xxx",
      "email": "user@example.com",
      "created_at": "2026-06-24T12:00:00Z"
    }
  ],
  "total": 15,
  "page": 1,
  "page_size": 20
}
```

### POST `.../participants`

Create a participant (creates a subject + email identity + participant in one
transaction).

**Request body:**

```json
{
  "email": "user@example.com",
  "subject_code": "optional-custom-code"
}
```

Returns a single participant object (201).

### PATCH `.../participants/{participant_id}`

Update the participant's email and/or subject code.

**Request body (all fields optional):**

```json
{
  "email": "new@example.com",
  "subject_code": "new-code"
}
```

Returns the updated participant object.

### DELETE `.../participants/{participant_id}`

Delete a participant record. Returns 204.

Blocked with 409 if the participant is assigned to an active survey link.

---

## Key details for frontend

- **Subjects vs participants:** every participant is a subject, but not every
  subject is a participant. Use the subject endpoints to see anonymous visitors
  and the participant endpoints to manage enrolled users.
- **Cross-linking:** subject responses include `participant_id` (non-null when
  enrolled). Participant responses include `subject_id`. Use these to navigate
  between the two views.
- `active_identity_count` and the detail `identities` list only include
  non-revoked identities. `revoked_at` is always `null` in current responses
  (included for forward-compatibility if `?include_revoked=true` is added
  later).
- Identity data never includes `user_id` or token hashes.
- Both subject and participant lists use `page` / `page_size` pagination with
  the same defaults and limits.
- TypeScript types are already generated in `schema.ts` via `sync-openapi.sh`.
