# Project Subject Identity and Access

Project-level participant records, identity attachments, reusable browser
recognition, assigned links, and the boundary between subject resolution and
submission-session creation.

> **Scope note.** This document explains how FlowForm recognises or creates a
> project subject before starting a survey session. It complements
> [architecture.md](architecture.md), [project-subjects.md](project-subjects.md),
> [schema/core-database-schema.md](schema/core-database-schema.md),
> [session-flows.md](session-flows.md), [api-structure.md](api-structure.md), and
> [backend-implementation.md](backend-implementation.md). It does not redefine
> encrypted answer storage, response locators, or answer revision mechanics.

---

## 1. Purpose

A FlowForm participant may begin anonymously and later become more strongly
identified.

Examples:

* an anonymous respondent opens a public survey;
* the same browser later opens another survey in the same project;
* a project administrator creates an assigned link for an existing subject;
* a respondent verifies an email address later;
* a respondent later signs in through Auth0;
* an authenticated identity or email identity is revoked without deleting the
  underlying participant history.

The subject model should preserve one stable project-level participant record
through these transitions.

---

## 2. Core model

```text
project_subject
    ├── zero or more identities
    │     ├── authenticated user identity
    │     └── normalized email identity
    │
    ├── zero or more reusable subject-recognition tokens
    │
    ├── zero or more assigned survey links
    │
    ├── zero or more submission sessions
    │
    └── zero or more IP observations
```

### 2.1 `project_subjects`

`project_subjects` is the stable project-level participant record.

```text
project_subjects.id
project_subjects.project_id
project_subjects.subject_code
project_subjects.created_at
```

`subject_code` is a project-scoped pseudonymous code. It must not be derived
from an email address, Auth0 identifier, user ID, or other identifying value.

An anonymous participant needs only a `project_subjects` row. Do not create a
fake anonymous identity row.

### 2.2 `project_subject_identities`

Identities are revocable attachments to a subject.

```text
project_subject_identities.id
project_subject_identities.project_id
project_subject_identities.project_subject_id
project_subject_identities.identity_type
project_subject_identities.user_id
project_subject_identities.normalized_email
project_subject_identities.verification_status
project_subject_identities.verified_at
project_subject_identities.attached_at
project_subject_identities.revoked_at
```

Initial identity types:

```text
authenticated_user
email
```

The table deliberately allows identity state to change independently from the
subject record.

### 2.3 `project_subject_tokens`

A subject-recognition token allows the backend to reconnect a browser to an
existing project subject across multiple survey sessions without requiring
sign-in.

Store only:

```text
SHA-256(raw_subject_recognition_token)
```

The raw token belongs only in a secure browser cookie. It is distinct from the
submission-session resume token.

### 2.4 `survey_links.assigned_subject_id`

An assigned survey link may point directly to an existing project subject.

This supports a participant who exists before the survey link is created, even
when the subject does not yet have a verified email address or user account.

### 2.5 `subject_ip_observations`

Store IP observations as separate append-only operational metadata rather than
placing a current IP address directly on a subject or session row.

This table may support abuse detection, duplicate-response review, fraud
investigation, and audit trails. Apply a retention policy because IP addresses
remain identifying metadata.

---

## 3. Three token types must remain separate

| Token | Purpose | Server-side storage | Browser transport |
|---|---|---|---|
| Survey-link token | Grants access through a general or assigned link | Prefix and hash on `survey_links` | Link URL initially, then request body during resolution or session start |
| Subject-recognition token | Reconnects a browser to a stable project subject across survey sessions | Hash on `project_subject_tokens` | Secure HttpOnly cookie |
| Submission resume token | Reconnects a browser to one active survey attempt | Hash on `submission_sessions` | Secure HttpOnly cookie |

Do not reuse one token for another purpose.

Do not expose raw recognition tokens, raw resume tokens, or raw link tokens in
logs, tracing metadata, response bodies, or persistent database columns.

---

## 4. Subject-resolution principles

Subject resolution happens after the backend resolves the project and survey
access channel but before the backend inserts a new `submission_sessions` row.

The resolver receives an internal access context such as:

```text
project_id
survey_id
survey_version_id
optional link_id
optional assigned_subject_id
optional assigned_email requirement
authentication context
optional raw subject-recognition cookie
```

It returns:

```text
optional project_subject_id
subject_resolution_source
optional new recognition token to issue after successful session start
```

### 4.1 Suggested precedence

Use the strongest explicit constraint first:

```text
1. Assigned subject from the resolved survey link
2. Authenticated user identity when sign-in is required or available
3. Verified email identity when the workflow requires email verification
4. Valid project-subject recognition token from the browser
5. Newly created anonymous project subject when project policy enables tracking
6. No project subject when the workflow intentionally permits untracked anonymity
```

A lower-priority signal must never silently override a higher-priority
constraint.

### 4.2 Conflict handling

Examples of conflicts:

* an assigned-subject link is opened by a browser recognised as another subject;
* an authenticated user is already attached to another subject in the project;
* a newly verified email is already attached to another active subject;
* a recognition token belongs to another project.

Do not silently rewrite relationships.

Return a safe conflict or access-denied result and route the case through an
explicit merge, verification, or support workflow.

### 4.3 Subject creation policy

Creating a `project_subjects` row for every anonymous browser visit is a
product decision.

Recommended default:

```text
Create the project subject during successful session start when the project
needs cross-survey recognition or subject-level analytics.
```

Possible privacy-minimising alternative:

```text
Leave submission_sessions.project_subject_id NULL for fully anonymous surveys
that do not need cross-survey continuity.
```

The access resolver should return the chosen policy explicitly rather than
assuming every survey behaves the same way.

---

## 5. Main access flows

### 5.1 Public slug or general-link entry

```text
Resolve survey and project
        ↓
Read optional subject-recognition cookie
        ↓
Resolve an existing project subject when the token is valid
        ↓
Otherwise create an anonymous subject only when project policy requires one
        ↓
Start submission session with optional project_subject_id
        ↓
Provision anonymous encrypted response envelope
        ↓
Issue resume cookie
        ↓
Issue or rotate subject-recognition cookie when appropriate
```

### 5.2 Assigned-subject link

```text
Resolve link token
        ↓
Load assigned_subject_id
        ↓
Confirm the assigned subject belongs to the survey project
        ↓
Apply any additional authentication requirement
        ↓
Start the session using the assigned subject
```

A browser recognition cookie may help detect conflicts but must not replace the
link assignment.

### 5.3 Assigned-email or authenticated link

```text
Resolve link token
        ↓
Require authentication when configured
        ↓
Compare the authenticated or verified email requirement
        ↓
Resolve or attach the subject identity
        ↓
Start the session using the resulting project subject
```

Do not attach an email identity merely because an unauthenticated browser typed
an email address. Verification rules must remain explicit.

### 5.4 Anonymous subject later signs in

```text
Resume existing submission session
        ↓
Load session project_subject_id
        ↓
Authenticate user through Auth0
        ↓
Check whether the authenticated identity is already attached elsewhere
        ↓
Attach identity, merge explicitly, or reject conflict
        ↓
Keep the same project subject whenever the attachment is valid
```

The original subject record remains the stable participant record.

---

## 6. Respondent-facing endpoint plan

The existing session API remains the primary respondent-facing surface.

### 6.1 Required v1 contract endpoints

```text
POST /api/v1/public/links/resolve

POST /api/v1/public/submission-sessions
GET  /api/v1/public/submission-sessions/current
PUT  /api/v1/public/submission-sessions/current/answers/{question_node_id}
POST /api/v1/public/submission-sessions/current/events/question-viewed
POST /api/v1/public/submission-sessions/current/complete
```

Subject recognition should initially happen inside link resolution and session
start. Do not require the browser to send `project_subject_id` in a JSON body.
During rollout, some of these routes may still be backed by temporary contract
stubs; the contract shape remains the target.

### 6.2 Link-resolution request

```json
{
  "token": "plaintext-link-token"
}
```

Suggested safe response shape:

```json
{
  "survey": {
    "id": 12,
    "title": "Customer intake"
  },
  "version": {
    "id": 31,
    "version_number": 4
  },
  "access": {
    "channel": "link",
    "requires_auth": true,
    "assignment": "subject",
    "can_start": true
  }
}
```

Public responses should not reveal:

```text
assigned_subject_id
assigned_email
project_subject_id
identity IDs
recognition-token hashes
```

The endpoint is a preview only. Session start must revalidate the raw link
token and access requirements.

### 6.3 Session-start request

Keep the current discriminated union:

```json
{
  "access": {
    "type": "public_slug",
    "public_slug": "customer-intake"
  }
}
```

or:

```json
{
  "access": {
    "type": "link_token",
    "token": "plaintext-link-token"
  }
}
```

Do not add these browser-controlled fields:

```text
project_subject_id
assigned_subject_id
user_id
normalized_email
subject_recognition_token
survey_version_id
```

The backend resolves them from the access context, authentication context, and
secure cookies.

### 6.4 Session-start response

The respondent-safe session response remains suitable:

```json
{
  "status": "in_progress",
  "started_at": "2026-06-11T01:20:00Z",
  "expires_at": "2026-06-18T01:20:00Z",
  "survey": {
    "id": 12,
    "title": "Customer intake"
  },
  "version": {
    "id": 31,
    "version_number": 4,
    "compiled_schema": {}
  },
  "answers": []
}
```

Cookies may include:

```text
flowform_submission_session=<raw-session-resume-token>
flowform_project_subject=<raw-subject-recognition-token>
```

Both cookies should be `HttpOnly`, `Secure`, and reviewed for an appropriate
`SameSite` policy.

The exact multi-project cookie strategy remains an implementation decision. If
a browser must retain recognition across multiple projects simultaneously,
consider a project-scoped cookie naming strategy or another bounded transport
format.

### 6.5 Optional later respondent endpoints

Add these only when the product includes an explicit identity-upgrade UI:

```text
POST /api/v1/public/submission-sessions/current/subject/email-verifications
POST /api/v1/public/submission-sessions/current/subject/email-verifications/confirm
POST /api/v1/public/submission-sessions/current/subject/attach-authenticated-user
DELETE /api/v1/public/submission-sessions/current/subject/recognition
```

Possible email-verification start request:

```json
{
  "email": "participant@example.com"
}
```

Possible response:

```json
{
  "status": "verification_required"
}
```

Keep these routes out of v1 until there is a real user flow that requires them.

---

## 7. Administrator endpoint plan

The exact administrator surface may be implemented later. The following route
shape gives the subject model a clear destination without forcing it into the
public session contract.

### 7.1 Project subject reads

```text
GET /api/v1/projects/{project_id}/subjects
GET /api/v1/projects/{project_id}/subjects/{subject_id}
```

Possible list item:

```json
{
  "id": "ce5b4881-0fc2-4640-bd19-44521c25cc31",
  "subject_code": "SUBJ-A8Q4X2",
  "identity_summary": {
    "has_verified_email": true,
    "has_authenticated_user": false
  },
  "created_at": "2026-06-11T01:20:00Z"
}
```

### 7.2 Subject creation

```text
POST /api/v1/projects/{project_id}/subjects
```

Possible request:

```json
{
  "subject_code": "SUBJ-A8Q4X2"
}
```

The backend may generate `subject_code` when omitted.

### 7.3 Identity attachment and revocation

```text
POST /api/v1/projects/{project_id}/subjects/{subject_id}/identities
POST /api/v1/projects/{project_id}/subjects/{subject_id}/identities/{identity_id}/revoke
```

Possible request:

```json
{
  "identity_type": "email",
  "email": "participant@example.com"
}
```

or:

```json
{
  "identity_type": "authenticated_user",
  "user_id": 42
}
```

Revocation should change `revoked_at`; it should not erase the identity row.

### 7.4 Recognition-token revocation

```text
POST /api/v1/projects/{project_id}/subjects/{subject_id}/tokens/{token_id}/revoke
```

The API may expose token metadata such as `created_at`, `last_used_at`, and
`revoked_at`, but never the token hash or raw token.

### 7.5 Survey-link create and update schemas

Existing survey-link management schemas should add:

```text
assigned_subject_id: UUID | null
```

Keep:

```text
assigned_email: string | null
requires_auth: boolean
```

Do not enforce an exclusive choice between `assigned_email` and
`assigned_subject_id`. A link may be assigned to a known subject and also
require sign-in as a specific email identity.

---

## 8. Service-layer plan

### 8.1 Core repositories

```text
ProjectSubjectRepository
ProjectSubjectIdentityRepository
ProjectSubjectTokenRepository
SubjectIpObservationRepository
SurveyLinkRepository
SubmissionSessionRepository
```

A repository should access only the core database. It should not provision
response envelopes or call KMS.

### 8.2 Submission and subject services

```text
SurveyAccessResolver
ProjectSubjectResolver
SubjectRecognitionTokenService
SubjectIdentityService
SubjectMergeService                 # later, only when conflict workflows exist
SubjectIpObservationRecorder
SessionStarter
```

### 8.3 Internal access context

Suggested internal domain shape:

```python
@dataclass(frozen=True)
class ResolvedSurveyAccess:
    project_id: int
    survey_id: int
    survey_version_id: int
    response_store_id: int
    link_id: int | None
    assigned_subject_id: UUID | None
    assigned_email: str | None
    requires_auth: bool
    subject_tracking_policy: str
```

Suggested subject resolution result:

```python
@dataclass(frozen=True)
class ResolvedProjectSubject:
    project_subject_id: UUID | None
    resolution_source: str
    issue_recognition_token: bool
```

### 8.4 Session-start orchestration

```text
1. Resolve and revalidate survey access.
2. Load authenticated user context when available.
3. Read the optional subject-recognition cookie.
4. Resolve or create the project subject according to policy.
5. Snapshot the response store and published survey version.
6. Create the core submission session.
7. Provision the anonymous response envelope.
8. Create the core session-started event.
9. Issue the session resume cookie only after both stores succeed.
10. Issue or rotate the subject-recognition cookie when appropriate.
11. Record the IP observation according to policy.
```

Subject resolution belongs before session creation. Envelope provisioning and
cryptography remain inside the existing submission service boundary.

### 8.5 Identity attachment orchestration

```text
1. Load the current or administrator-selected project subject.
2. Normalise the proposed identity value.
3. Verify that the caller is authorised to attach the identity.
4. Detect an existing active attachment or cross-subject conflict.
5. Attach, reject, or route to an explicit merge workflow.
6. Record verification and revocation timestamps separately.
```

Do not silently merge subjects in a repository method.

---

## 9. Testing plan additions

### 9.1 Subject resolution

Verify:

* anonymous access may create a project subject when tracking is enabled;
* fully anonymous access may leave `project_subject_id` null when policy allows;
* a valid recognition token reconnects to the same project subject;
* an expired or revoked recognition token is rejected;
* a token from another project cannot bind the session;
* an assigned-subject link binds the expected subject;
* an assigned-subject conflict does not silently reassign a subject;
* an assigned-email link enforces its authentication requirement.

### 9.2 Identity attachments

Verify:

* an authenticated user identity attaches to one project subject;
* a verified email identity attaches to one project subject;
* duplicate active authenticated-user identities are rejected per project;
* duplicate active verified email identities are rejected per project;
* unverified email claims do not silently become verified identities;
* revocation preserves the identity history row;
* identity conflicts enter an explicit conflict path.

### 9.3 Recognition tokens

Verify:

* only the token hash reaches PostgreSQL;
* raw tokens are returned only through a secure-cookie path;
* expired and revoked tokens fail resolution;
* token rotation does not invalidate the stable subject;
* recognition tokens are never treated as submission resume tokens.

### 9.4 IP observations

Verify:

* an observation may attach to a subject, a session, or both according to the
  final schema;
* a subject and session from different projects cannot be combined;
* retention and deletion behavior matches project policy;
* logs and error responses do not leak raw IP data unnecessarily.

---

## 10. Open decisions

The schema can land before these details are finalised:

1. Whether every anonymous survey creates a project subject or whether this is
   controlled by a project or survey policy.
2. The exact cookie strategy for retaining subject-recognition tokens across
   multiple projects in one browser.
3. Whether email identity attachment exists in v1 or remains a later workflow.
4. Whether subject merge tooling is required for administrators in v1.
5. The retention period and access permissions for `subject_ip_observations`.
6. Whether recognition tokens rotate on every use, periodically, or only when
   nearing expiry.

Keep these as explicit product decisions. Do not let them become accidental
behavior hidden inside the session-start implementation.
