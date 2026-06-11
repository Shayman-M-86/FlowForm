# Project Subjects

Project-scoped respondent identity relation for the session and response
encryption work.

## Purpose

`project_subjects` is the core database record for a respondent identity within
one project.

It answers one question:

```text
Which project-level subject, if any, is this submission session associated with?
```

The relation is intentionally small. Identity attachments, recognition tokens,
survey access links, sessions, and IP observations attach around it.

## Subject Record

```text
project_subjects
    id              UUID primary key
    project_id      BIGINT, required
    subject_code    TEXT, required, unique within project
    created_at      TIMESTAMPTZ
```

`id` is the internal durable key. It is used by foreign keys and backend joins.

`subject_code` is the stable project-scoped participant code. FlowForm can
generate it, or a controlled import/integration path can supply it.

The subject record can represent an anonymous participant, an invited
participant, an imported participant, or an authenticated user once an identity
attachment exists.

## Identity Attachments

```text
project_subject_identities
    id
    project_id
    project_subject_id
    identity_type          email | authenticated_user
    user_id                populated for authenticated_user
    normalized_email       populated for email
    verification_status
    verified_at
    attached_at
    revoked_at
```

Identity rows are revocable attachments to the stable subject.

An authenticated user identity gives one active user-to-subject attachment per
project. An email identity supports verification history and email-assigned
flows. A subject can exist without an identity row.

## Recognition Tokens

```text
project_subject_tokens
    id
    project_id
    project_subject_id
    token_hash
    expires_at
    last_used_at
    revoked_at
    created_at
```

Subject-recognition tokens reconnect a browser or project-specific flow to a
stable subject across surveys in the same project. The stored value is a
SHA-256 hash of the raw token.

## Survey Links

Survey links can optionally attach to a subject:

```text
survey_links.assigned_subject_id -> project_subjects.id
```

`survey_links.project_id` should be present so the database can prove the link,
survey, and assigned subject all belong to the same project.

## Submission Sessions

The core session points to the subject by UUID:

```text
submission_sessions.project_subject_id -> project_subjects.id
```

The composite foreign key:

```text
(submission_sessions.project_id, submission_sessions.project_subject_id)
    -> (project_subjects.project_id, project_subjects.id)
```

keeps session-to-subject attachment project-scoped.

When access resolution identifies a project subject, session start stores:

```text
submission_sessions.project_subject_id = project_subjects.id
```

When access resolution is anonymous, session start stores:

```text
submission_sessions.project_subject_id = NULL
```

## Token Roles

| Token | Purpose | Stored value |
|---|---|---|
| Survey link token | Grants access to start through a link | Prefix and hash on `survey_links` |
| Subject-recognition token | Reconnects a browser to a stable project subject | Hash on `project_subject_tokens` |
| Submission resume token | Reconnects a browser to one active survey attempt | Hash on `submission_sessions` |
