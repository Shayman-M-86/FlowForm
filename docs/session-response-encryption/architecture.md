# Architecture

This document explains the session/response encryption architecture and marks
the boundary between implemented code and target design. For exact schema
details, see [data-model.md](data-model.md). For route behavior, see
[api-surface.md](api-surface.md). For unfinished work, see
[remaining-work.md](remaining-work.md).

## Current Implementation Boundary

Implemented now:

- Core schema for project subjects, identities, participants, recognition
  tokens, submission sessions, events, and response-envelope tables.
- Public-link resolution and authenticated-link participant checks.
- Subject resolution through `ProjectSubjectResolver`.
- Session start through `SessionStarter`.
- Placeholder contracts for resume, answer save, question-viewed events,
  completion, and admin response reads.

Not implemented yet:

- Response-envelope creation during session start.
- Resume service and canonical-answer reads.
- Answer-save service, answer locators, revisions, and idempotency.
- Completion/lifecycle service.
- KMS, linkage-secret HMAC locators, DEK handling, AES-GCM encryption, AAD,
  key caching, and key rotation.
- Admin read/export/delete paths backed by real response data.

## Design Goals

FlowForm needs to collect answers while keeping identifying application
metadata separate from sensitive answer payloads.

The core database stores application metadata:

- projects, surveys, and published survey versions;
- public and restricted survey links;
- project-scoped respondent identity records;
- submission sessions and session status;
- session analytics events.

The response database stores answer material:

- anonymous response envelopes;
- logical answer rows;
- immutable answer revisions;
- ciphertext, nonces, and wrapped DEKs.

The response database must not store user IDs, project IDs, survey IDs,
survey-link IDs, plaintext question IDs, plaintext answers, the core session
UUID, emails, IP addresses, project-subject IDs, participant IDs, identity
IDs, or recognition tokens.

## Storage Split

FlowForm uses two PostgreSQL databases.

```text
Core PostgreSQL database
  surveys and versions
  survey links
  project subjects, identities, participants, tokens
  submission sessions
  analytics events

        HMAC-derived locators
        no direct foreign key

Response PostgreSQL database
  response envelopes
  logical answers
  immutable answer revisions
  wrapped DEKs
  ciphertext and nonces
```

There is no SQL foreign key between the databases. The intended link is
cryptographic: the backend derives `response_envelopes.session_locator` from
`submission_sessions.id` and versioned linkage-key material. That design is
documented in [cryptography-plan.md](cryptography-plan.md), but the real
locator and encryption services are not implemented yet.

## Core Identity Model

The core identity model is project-scoped.

- `project_subjects` is the pseudonymous subject row for one respondent
  inside one project.
- `project_subject_identities` attaches revocable identities to a subject,
  such as email or authenticated-user identity.
- `project_participants` binds one subject plus one identity into the
  assignment target used by `survey_links.assigned_participant_id`.
- `project_subject_tokens` stores hashed recognition tokens for returning
  respondent recognition.
- `subject_ip_observations` stores core-side IP metadata for future policy
  and abuse controls.

`submission_sessions.project_subject_id` may point to a resolved subject. A
null value means the core session is anonymous at the identity layer. The
response database never receives that subject ID; it sees only opaque
locators.

## Session Lifecycle

The intended lifecycle is:

1. Resolve access from a public slug or survey-link token.
2. Resolve a subject from server-owned context: assigned participant,
   authenticated-user identity, recognition token, optional anonymous-subject
   policy, or none.
3. Create a core `submission_sessions` row with a frozen survey version and
   hashed browser resume token.
4. Create a response envelope tied to the session by a derived locator.
5. Resume the session by hashing the browser token and loading canonical
   answers.
6. Save answers as immutable encrypted revisions.
7. Complete the session once required canonical answers are valid.
8. Let admin reads/export/delete go through authorization plus decrypt paths.

Only steps 1-3 are implemented today. Steps 4-8 are tracked in
[remaining-work.md](remaining-work.md).

## Answer Storage Model

The response side is shaped around append-only revision history:

```text
response_envelopes
    one envelope per submission session locator
    contains wrapped DEK metadata

response_answers
    one logical answer slot per envelope/question locator
    points to latest_revision_id

response_answer_revisions
    immutable encrypted revisions
    carries ciphertext, nonce, revision_number, client_mutation_id
```

`response_answers.latest_revision_id` gives fast access to the current
canonical answer without scanning revision history. Earlier revisions remain
available for history/audit workflows and are never overwritten.

## Technology Boundaries

Backend code should keep explicit database boundaries:

- core repositories receive a core database session;
- response repositories receive a response database session;
- cross-database orchestration belongs in services;
- domain modules own policy decisions and invariants;
- API handlers stay thin.

The frontend should receive only public contracts: frozen survey content,
session state, validation errors, and answer-save/completion responses. It
must never receive a DEK, linkage secret, KMS key reference, HMAC locator, or
answers belonging to another respondent.

## Operational Shape

The final implementation needs:

- Secrets Manager for versioned linkage secrets;
- KMS for response DEK generation/unwrapping;
- IAM policies that separate linkage-secret access from response-key access;
- CloudTrail visibility for KMS operations;
- log and Sentry sanitization for tokens, answers, plaintext keys, and raw
  secrets;
- reconciliation for cross-database partial failures;
- metrics for starts, saves, completions, decrypt failures, KMS failures, and
  reconciliation repairs.

Those operational items are still future work unless explicitly noted in
[remaining-work.md](remaining-work.md).
