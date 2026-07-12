---
title: Data flows
document_type: architecture
status: draft
authority: canonical
verified_against_commit: ed0fb65df856e18807ee243b4bca512a8d0442b0
tags: [backend, frontend, security]
related_code:
  - "../../backend/app/api/v1/"
  - "../../backend/app/services/surveys.py"
  - "../../backend/app/services/public_submissions/"
  - "../../backend/app/services/results.py"
  - "../../backend/app/crypto/"
  - "../../backend/app/schema/orm/"
related_docs:
  - "Component map"
  - "Trust boundaries"
  - "Surveys and versioning"
  - "Links and subjects"
  - "Submissions"
  - "Responses and encryption"
---

# Data flows

Documents major information flows that cross components and trust boundaries.

![Overview of FlowForm data flows: Studio and respondent clients talk to the Flask backend, which writes to a core database and a response database linked only by derived opaque locators|606](assets/data-flows-overview.svg)

## Scope

This page shows the direction and ownership of important runtime information. It
does not specify every endpoint, field, permission, crypto primitive, or failure;
those details belong in the linked domain, workflow, implementation, and
reference pages.

## The five flows at a glance

| # | Flow | Started by | Core database | Response database |
|---|------|-----------|---------------|-------------------|
| 1 | [Survey authoring and publication](#survey-authoring-and-publication) | Studio user | writes drafts, versions, compiled rules | — |
| 2 | [Respondent entry and session start](#respondent-entry-and-session-start) | Respondent browser | writes session metadata | writes encrypted envelope |
| 3 | [Answer save, events, and completion](#answer-save-events-and-completion) | Respondent browser | writes answer slots and events | upserts ciphertext |
| 4 | [Results read and export](#results-read-and-export) | Studio user | reads metadata | reads ciphertext (decrypted server-side) |
| 5 | [Recovery flow](#recovery-flow) | Reconciliation service | marks orphaned sessions `abandoned` | checks envelope presence |

The two databases are never joined in SQL. Every cross-database association goes
through a derived opaque locator, so the response side holds ciphertext without
core identifiers, and the core side holds identifiers without answer content.

## Survey authoring and publication

```mermaid
flowchart LR
    U[Authorized Studio user] --> C[Studio API client]
    C --> E[Authenticated Studio endpoint]
    E --> S[Access check + survey service]
    S --> Core[(Core database)]
```

Draft questions and scoring rules are stored against a survey version. Publishing
checks that the version is a non-empty draft, compiles its nodes and scoring
rules, ensures response-storage and survey-encryption-key prerequisites, and
marks it as the survey's active published version. Respondent collection then
binds to that version. [[Surveys and versioning]] owns the lifecycle and
[[Projects and access]] owns authorization semantics.

## Respondent entry and session start

```mermaid
sequenceDiagram
    participant B as Respondent browser
    participant API as Respondent API
    participant Resp as Response database
    participant Core as Core database

    B->>API: public slug or link token<br/>(optional authenticated identity + recognition cookie)
    API->>API: access + subject resolution,<br/>select published version and response store
    API->>API: derive session locator,<br/>encrypt response envelope
    API->>Resp: commit encrypted envelope
    API->>Core: commit session metadata
    alt core commit fails
        API->>Resp: attempt envelope delete
        Note over API,Resp: failed cleanup is logged<br/>as a critical orphan condition
    end
    API-->>B: session + optional recognition cookies
```

The access resolver selects a published survey version and response store. The
subject flow may associate the attempt with a project subject, depending on the
access method, authenticated actor, assigned participant, and recognition state.
The service creates core session metadata and a response-side envelope linked by
an opaque derived locator. [[Links and subjects]] owns identity resolution;
[[Submissions]] owns the attempt lifecycle.

> [!WARNING]
> Session start crosses two independent database transactions. The response
> envelope is committed before the core transaction; if the core commit fails,
> the service attempts to delete the envelope. Failed cleanup is logged as a
> critical orphan condition. This is compensation, not an atomic cross-database
> commit.

## Answer save, events, and completion

```mermaid
sequenceDiagram
    participant B as Respondent browser
    participant API as Respondent API
    participant Core as Core database
    participant Resp as Response database

    B->>API: session cookie + answer command
    API->>Core: load session, lock it,<br/>validate question/answer against its version
    API->>API: create answer slot,<br/>derive opaque answer locator,<br/>encrypt answer payload
    API->>Core: commit answer slot
    API->>Resp: upsert ciphertext, nonce,<br/>mutation ID, opaque locator
    Note over Resp: never receives core question<br/>or session identifiers
```

The response database receives the current ciphertext, nonce, mutation ID, and
opaque locator, not the core question or session identifiers. Question-viewed
and answer-saved analytics remain core-side events. Completion locks the core
session, moves it from `in_progress` to `completed`, records a best-effort event,
and evicts the cached write context. Detailed payload and encryption contracts
belong in [[Responses and encryption]].

> [!WARNING]
> Answer save also uses sequential core and response commits. A committed core
> slot can therefore exist without a response answer if the later response write
> fails; the results read path can report that the encrypted answer is absent.

## Results read and export

```mermaid
flowchart LR
    U[Authorized Studio user] --> P[Results endpoint +<br/>survey permission check]
    P --> Core[(Core: subjects, sessions,<br/>slots, events)]
    Core --> L[Opaque locator<br/>resolution]
    L --> Resp[(Response: envelope +<br/>encrypted answers)]
    Resp --> D[Server-side<br/>decryption]
    D --> V[Structured view or<br/>JSON/CSV export]
```

Management reads begin from core metadata and retrieve response-side data only
when requested and available. Decryption occurs in the backend; the response
database does not gain core identifiers through this read path. Authorization,
redaction, and export contracts require deeper review in [[Security model]],
[[Responses and encryption]], and [[Backend implementation]].

## Recovery flow

```mermaid
flowchart TD
    R[Reconciliation service] --> S[Scan in-progress<br/>core sessions]
    S --> D[Derive session locators]
    D --> C{Response envelope<br/>exists?}
    C -->|yes| K[Leave session unchanged]
    C -->|no| A[Mark session abandoned]
```

The reconciliation service scans in-progress core sessions, derives their
session locators, and checks for response envelopes. A session whose envelope is
missing is marked `abandoned`; matched sessions are left unchanged.

> [!NOTE]
> The inspected code defines this operation, but this pass did not find evidence
> that a deployed scheduler or operator workflow invokes it.

## Knowledge boundaries

- The page describes application flow from static source; it does not establish
  production traffic, health, scale, or deployed topology.
- Cross-database compensation and reconciliation do not cover every possible
  partial failure. Operational ownership and retry policy remain unresolved.
- Cache, KMS, and secret-loading mechanics are intentionally left to
  [[Security model]], [[Configuration implementation]], and
  [[Secrets and configuration]].

## Related documents

- [[Component map]]
- [[Trust boundaries]]
- [[Surveys and versioning]]
- [[Links and subjects]]
- [[Submissions]]
- [[Responses and encryption]]
