# Session Flows

Respondent access resolution, session start/resume, question-view events, completion, abandonment, and expiry.

## 12. Session lifecycle overview

```text
Resolve survey access
        ↓
Start submission session
        ↓
Create anonymous response envelope
        ↓
Issue browser resume token
        ↓
Render frozen survey version
        ↓
View questions and save answers
        ↓
Insert immutable answer revisions
        ↓
Move canonical latest pointers forward
        ↓
Complete or abandon session
        ↓
Read, export, retain or delete response
```

---

## 13. Flow: resolving survey access

A respondent may enter through:

* a public survey slug;
* a general survey link;
* an assigned link;
* an authenticated workflow;
* another supported project-specific access method.

The backend must resolve the entry method before creating a submission session.

### 13.1 Resolve the survey

Load:

```text
survey
published survey version
compiled immutable schema
```

Reject access if:

* no published version exists;
* the survey is not available through the requested access channel;
* the link is inactive;
* the link has expired;
* an assigned-link requirement is not satisfied.

### 13.2 Bind the session to one frozen survey version

A submission session must store:

```text
survey_version_id
```

This is fixed at session creation.

If the survey owner publishes a newer version halfway through the respondent's session, the active respondent continues using the original version.

Never silently move an in-progress session to a different survey version.

### 13.3 Resolve the optional project subject

After resolving the project and access channel, resolve an optional stable
project subject. Inputs may include an assigned subject from the link, the
authenticated user context, a verified email requirement, a reusable
subject-recognition cookie, or a project-specific subject code.

Examples:

* an authenticated respondent maps through `project_subject_identities.user_id`;
* an assigned link maps to an invited or imported project participant;
* a subject-recognition token maps through `project_subject_tokens.token_hash`;
* a project-specific integration supplies a recognized `subject_code`.

Use the strongest explicit constraint first. Do not silently override an
assigned subject with a weaker browser-recognition signal.

When a subject is found, pass the internal UUID forward:

```text
project_subjects.id
```

and store it later as:

```text
submission_sessions.project_subject_id
```

If no project subject is found, create an anonymous subject only when project
policy requires cross-survey continuity or subject-level analytics. Otherwise
keep `project_subject_id` null and treat the session as fully anonymous at the
core identity layer.

---

## 14. Flow: starting a submission session

### 14.1 Inputs

The backend receives the resolved access context:

```text
survey_version_id
optional link_id
optional project_subject_id
```

### 14.2 Generate session values

Generate:

```text
submission_session_id = random UUID
raw_browser_token     = random 32-byte token
browser_token_hash    = SHA-256(raw_browser_token)
envelope_id           = random UUID
```

### 14.3 Insert the core session

Create the core `submission_sessions` row:

```text
id                         = submission_session_id
link_id                    = optional link ID
project_subject_id         = optional project_subjects.id
survey_version_id          = frozen published version
browser_session_token_hash = token hash
linkage_key_version        = active linkage version
session_status             = in_progress
started_at                 = now
expires_at                 = configured expiry
last_activity_at           = now
```

Insert a core analytics event:

```text
session_started
```

### 14.4 Derive the anonymous response locator

Retrieve the active linkage secret from the in-memory cache or Secrets Manager.

Calculate:

```text
session_locator
```

### 14.5 Generate the DEK

Create the response envelope UUID first.

Call KMS `GenerateDataKey` using the response-envelope KEK and the non-sensitive encryption context.

Store:

```text
wrapped_dek
kms_key_arn
kms_context_version
crypto_version
```

Keep the plaintext DEK only in memory.

### 14.6 Insert the response envelope

Create:

```text
response_envelopes
```

using:

```text
id
session_locator
linkage_key_version
wrapped_dek
kms_key_arn
kms_context_version
crypto_version
created_at
```

### 14.7 Return success only after both stores succeed

Do not expose the session to the browser until:

* the core session exists;
* the response envelope exists;
* the resume-token cookie has been prepared.
* any subject-recognition cookie has been prepared.

If envelope creation fails after the core row was inserted:

* delete or invalidate the unexposed core session;
* record an internal error;
* do not issue the resume token;
* return a safe server error.

Because there is no distributed transaction, a crash can still leave a partial row. A reconciliation task should identify and clean old incomplete sessions.

---

## 15. Flow: resuming a session

### 15.1 Receive the browser token

Read the raw resume token from the secure browser cookie.

Hash it:

```text
SHA-256(raw_browser_token)
```

Query the core database by:

```text
browser_session_token_hash
```

### 15.2 Validate the core session

Reject the request if:

* no matching session exists;
* the session has expired;
* the session is abandoned;
* the session is already completed and the requested action requires editing;
* the frozen survey version can no longer be loaded.

### 15.3 Derive the response envelope locator

Read:

```text
submission_sessions.id
submission_sessions.linkage_key_version
```

Load the matching linkage secret.

Derive:

```text
session_locator
```

Query:

```text
response_envelopes.session_locator
```

### 15.4 Load canonical answers

Join:

```text
response_answers
    → latest_revision_id
    → response_answer_revisions
```

Only the current revision for each logical answer needs to be decrypted for a normal resume request.

### 15.5 Reconstruct respondent state

For each decrypted current payload:

1. Verify the real question-node UUID exists in the frozen survey version.
2. Recompute the answer locator.
3. Confirm that the recomputed locator matches the row.
4. Validate the payload shape.
5. Restore the answer into the respondent state.
6. Re-run survey rules from the compiled schema.

---

## 16. Flow: recording a question-view event

When a respondent views a question, the frontend may send:

```text
question_node_id
```

The backend validates that the node belongs to the frozen survey version.

Insert a core analytics event:

```text
event_type       = question_viewed
session_id       = current session
question_node_id = validated node ID
received_at      = server timestamp
```

These events are analytics metadata.

They are not part of the authoritative response payload.

If the analytics event fails, the respondent should still be allowed to continue the survey.

To avoid unnecessary traffic, the frontend may avoid repeatedly sending the same question-view event during one page render.

---

## 22. Flow: completing a session

### 22.1 Completion request

The browser sends a completion request using the resume-token cookie.

### 22.2 Lock the session

Lock the core submission-session row.

Confirm:

```text
session_status = in_progress
```

If it is already completed, return the existing completed state. Completion should be idempotent.

### 22.3 Load canonical answers

Derive the session locator.

Load the response envelope.

Load the current revision for every logical answer.

Decrypt the canonical answer set.

### 22.4 Validate the final answer set

Use the frozen compiled schema to validate:

* required questions;
* visible rule path;
* answer shapes;
* cleared answers;
* completion requirements;
* any scoring or rule-engine requirements that must be evaluated before submission.

### 22.5 Mark the core session completed

Update:

```text
session_status = completed
completed_at   = now
last_activity_at = now
```

Insert:

```text
session_completed
```

After completion, respondent answer saves are rejected.

The encrypted response rows do not need to be rewritten.

---

## 23. Flow: abandonment and expiry

### 23.1 Expiry

Each session stores:

```text
expires_at
last_activity_at
session_status
```

A scheduled maintenance process marks stale in-progress sessions as abandoned.

Example rule:

```text
if session_status = in_progress
and expires_at < now
then session_status = abandoned
```

### 23.2 Retention after abandonment

Do not automatically delete abandoned response data unless the project retention policy requires deletion.

An abandoned response may still be useful for:

* partial-response analysis;
* dropout analytics;
* support investigation;
* research retention policies.

### 23.3 Resuming abandoned sessions

The default behaviour should reject edits after abandonment.

A future project setting may permit controlled reactivation.

---
