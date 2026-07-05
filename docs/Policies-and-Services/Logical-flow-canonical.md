# Public Submissions — Logical Flow

One-page reference. Full policy in `Flows/` and `core-policies.md`.

---

## Pipeline (every entry point runs this in order)

```text
Request
  │
  ├─ 1. ACCESS RESOLUTION      → SubmissionAccessGrant
  ├─ 2. TOKEN LOOKUP           → RecognitionTokenResult | None
  ├─ 3. SUBJECT RESOLUTION     → SubjectResolutionResult
  ├─ 4. MERGE (if needed)      → canonical_subject_id written
  ├─ 5. IDENTITY WRITE         → project_subject_identity written (if needed)
  ├─ 6. TOKEN ACTION           → recognition cookie raw value | None
  ├─ 7. SESSION CREATE         → submission_session written
  ├─ 8. LINK CONSUME           → used_at written (single-use links only)
  └─ 9. COMMIT                 → single atomic commit, cookie set on response
```

---

## Step 1 — Access resolution (`AccessResolver`)

Validates how the respondent entered. Does not touch subjects or tokens.

| Input | What is checked | Error if fails |
|---|---|---|
| public slug | survey exists, published | `SurveyNotFoundBySlugError`, `SurveyNotPublishedError` |
| link token | token hash, link active, survey published | `LinkNotFoundError`, `LinkInactiveError` |

**Output:** `SubmissionAccessGrant` — access method, link id, assigned subject id, is_single_use, requires_auth.

---

## Step 2 — Token lookup (`SubjectTokenService.lookup`)

Checks the browser `recognition_token` cookie. Never raises — returns `None` if absent/invalid.

Valid while: not expired, not revoked, same `project_id`, hash matches.

**Output:** `project_subject_id`, `canonical_subject_id`, `is_canonical` — or `None`.

---

## Step 3 — Subject resolution (`SubjectResolver`)

Picks the final canonical `ProjectSubject`. Two branches:

### Open-access (public slug, general link)

Authority order: **logged-in identity > token subject > new anonymous subject**

| Logged in | Token | Identity exists | Final subject | Token action |
|---|---|---|---|---|
| no | none | — | new anonymous | issue |
| no | valid | — | token subject | mark_used |
| yes | none | no | new subject | create identity + issue |
| yes | valid | no | token subject | attach identity + mark_used |
| yes | none | yes | identity subject | issue |
| yes | valid, same canonical | yes | identity subject | mark_used (or rotate to canonical) |
| yes | valid, different canonical | yes | identity subject | merge token subject + rotate |

### Assigned-access (private link, authenticated link, account-linking)

Authority order: **assigned subject always wins**

| Token | Final subject | Token action |
|---|---|---|
| none | assigned subject | issue |
| valid, same canonical | assigned subject | keep |
| valid, different canonical | assigned subject | merge token subject + rotate |

Authenticated link adds an extra guard: logged-in user must match the assigned identity — rejected before subject resolution if not.

---

## Step 4 — Merge

When a weaker subject loses:
- `weaker.canonical_subject_id = stronger.id`
- stronger subject remains canonical (`canonical_subject_id = null`)
- never merge a subject into itself, never create chains

---

## Step 5 — Identity write

Only when `needs_identity_write = True` (two cases):
- logged in, no token, no identity → new subject, create identity
- logged in, valid token, no identity → attach identity to token subject

---

## Step 6 — Token action (`SubjectTokenService.apply_token_action`)

| Action | What happens | Returns |
|---|---|---|
| `issue` | create new token for final subject | raw token |
| `rotate` | revoke old + create new for final subject | new raw token |
| `mark_used` | stamp `last_used_at`, no new token | existing raw token |
| `keep` | no writes | `None` |
| `none` | no writes | `None` |

`last_used_at` is only stamped on open-access paths (public slug, general link). Assigned-link paths do not count the token as recognition authority.

---

## Step 7 — Session create

`submission_session` row written. Points to final canonical `project_subject_id`.

---

## Step 8 — Link consume (single-use links only)

`survey_links.used_at` set. Private and authenticated links only. General links are reusable and never consumed.

---

## Step 9 — Commit

Single `commit_with_err_handle`. All prior writes are flushes only (unit-of-work). If commit fails, everything rolls back — no partial state.

Contexts passed to error handler: `[session, link]` when link consumed, `[session]` otherwise.

---

## Account-linking (pre-session flow)

Runs at `POST /verify-participant`, before any session start.

1. Validate link is `authenticated` type
2. Match logged-in user email to assigned identity email
3. Link `user_id` to assigned identity
4. Run `resolve_assigned_subject` to reconcile browser token against assigned subject
5. Return new recognition cookie if token was rotated

Next session start on this link then runs the normal authenticated-link pipeline.

---

## Flow matrix (all 19 rows implemented)

| # | Entry | Auth | Token | Final subject | Token action | Link consumed |
|---|---|---|---|---|---|---|
| 1 | public slug | no | none | new anon | issue | no |
| 2 | public slug | no | valid | token subject | mark_used | no |
| 3 | public slug | yes | none | identity subject | issue | no |
| 4 | public slug | yes | same canonical | identity subject | mark_used | no |
| 5 | public slug | yes | diff canonical | identity subject | merge + rotate | no |
| 6 | general link | no | none | new anon | issue | no |
| 7 | general link | no | valid | token subject | mark_used | no |
| 8 | general link | yes | none | identity subject | issue | no |
| 9 | general link | yes | same canonical | identity subject | mark_used | no |
| 10 | general link | yes | diff canonical | identity subject | merge + rotate | no |
| 11 | private link | any | none | assigned | issue | yes |
| 12 | private link | any | same canonical | assigned | keep | yes |
| 13 | private link | any | diff canonical | assigned | merge + rotate | yes |
| 14 | auth link | no | any | **rejected** | — | no |
| 15 | auth link | yes, match | none | assigned | issue | yes |
| 16 | auth link | yes, match | same canonical | assigned | keep | yes |
| 17 | auth link | yes, match | diff canonical | assigned | merge + rotate | yes |
| 18 | auth link | yes, no match | any | **rejected** | — | no |
| 19 | account-linking | yes, email match | diff canonical | assigned | merge + rotate | no |

---

## Service map

| Class | File | Responsibility |
|---|---|---|
| `AccessResolver` | `core/access_resolver.py` | Step 1 — validate entry method |
| `SubjectTokenService` | `core/subject_token.py` | Steps 2 + 6 — lookup and apply token action |
| `SubjectResolver` | `core/subject_resolver.py` | Step 3 — pick final subject, plan merge/identity |
| `SessionStarter` | `core/session_starter.py` | Orchestrates steps 1–9, owns the transaction |
| `SurveyResolveService` | `api/survey_resolve.py` | Survey preview + account-linking endpoint |
| `SessionManagementService` | `api/session_management.py` | Route-layer wrapper for `SessionStarter` |

---

## Out of scope (not yet addressed)

- Response DB write at session start (vs. at first submission)
- `subject_ip_observations` logging
- `resolve_link` preview path identity guard for authenticated links
