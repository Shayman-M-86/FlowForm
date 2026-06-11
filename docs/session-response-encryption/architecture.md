# Architecture

Purpose, design goals, technology choices, database responsibilities, and the high-level split between core and response storage.

## 1. Purpose of this document

This document describes how FlowForm should create, resume, complete, and
administer survey submission sessions while keeping sensitive answer data
encrypted and separated from identifying application metadata.

It covers:

* the responsibilities of the core and response databases;
* the identifiers, secrets, and locators used to connect the two stores without
  exposing respondent identity in the response database;
* the lifecycle of a respondent submission session;
* encrypted answer storage, revision history, and canonical-answer reads;
* operational concerns such as key rotation, logging, failure handling, and
  testing.

## 2. Main design goals

The submission system should satisfy the following requirements.

### 2.1 Separate identifying metadata from sensitive answers

The core database stores application metadata:

* projects;
* surveys;
* published survey versions;
* access links;
* optional project subject records;
* submission sessions;
* session status;
* session analytics events.

The response database stores encrypted answer payloads:

* anonymous response envelopes;
* logical answer records;
* immutable answer revisions;
* encrypted answer ciphertext;
* encryption nonces;
* wrapped data-encryption keys.

The response database should not store:

* user IDs;
* project IDs;
* survey IDs;
* access-link IDs;
* plaintext question IDs;
* plaintext answers;
* the core submission-session UUID.

This means the response database remains difficult to interpret if it is accessed in isolation.

### 2.2 Preserve answer history

A respondent may change an answer halfway through a survey.

The system must keep:

* the newest successfully saved answer;
* the complete history of earlier saved values;
* the order in which revisions were created;
* a fresh encryption nonce for every saved revision.

Earlier answer ciphertext must never be overwritten.

### 2.3 Allow fast access to the current answers

The system should not scan all revisions every time it renders a resumed survey or exports a response.

Each logical answer has one canonical pointer:

```text
response_answers.latest_revision_id
```

That pointer identifies the newest successfully saved encrypted revision.

### 2.4 Avoid unnecessary KMS calls

AWS KMS should protect important cryptographic keys, but it should not be called for every small operation.

The normal answer-save path should encrypt locally after the server has obtained the session DEK.

### 2.5 Support future customer-managed response storage

The response repository boundary should remain clean enough that a future customer-managed response database can be introduced without redesigning the entire core application.

---

## 3. High-level architecture

FlowForm uses two PostgreSQL databases.

```text
┌─────────────────────────────┐
│ Core PostgreSQL database    │
│                             │
│ Surveys and versions        │
│ Links                       │
│ Optional project subjects   │
│ Submission sessions         │
│ Analytics events            │
└──────────────┬──────────────┘
               │
               │ HMAC-derived locators
               │ No direct foreign key
               │
┌──────────────▼──────────────┐
│ Response PostgreSQL database│
│                             │
│ Anonymous envelopes         │
│ Logical answers             │
│ Immutable answer revisions  │
│ Wrapped DEKs                │
│ Ciphertext and nonces       │
└─────────────────────────────┘
```

The databases are connected only through deterministic opaque locators created by the backend.

There is deliberately no cross-database foreign key.

---

## 4. Technology set

### 4.1 Backend application

The backend uses:

* Python;
* Flask;
* plain SQLAlchemy 2.0;
* Pydantic v2 for API validation;
* Boto3 for AWS integration;
* the Python `cryptography` package for local authenticated encryption.

The backend should continue using explicit SQLAlchemy sessions:

```text
core_db_session
response_db_session
```

Do not hide the two databases behind one implicit global session.

Each repository should receive the database session it requires.

### 4.2 Databases

Use two independent PostgreSQL databases:

```text
flowform_core
flowform_response
```

They may initially run on the same PostgreSQL server or cluster, but they must remain logically separate:

* separate database names;
* separate SQLAlchemy engines;
* separate credentials;
* separate migrations;
* separate repository modules;
* separate backup and retention considerations.

The response database should be treated as the more sensitive store.

### 4.3 AWS services

Use:

* AWS Key Management Service, or KMS;
* AWS Secrets Manager;
* AWS Identity and Access Management, or IAM;
* AWS CloudTrail for KMS audit visibility.

### 4.4 Frontend

The respondent-facing survey UI uses the existing React application.

The frontend is responsible for:

* resolving the survey access method;
* starting or resuming a session;
* rendering the frozen published survey version;
* submitting answer mutations;
* sending question-view events where required;
* completing the session.

The frontend must never receive:

* a DEK;
* a linkage secret;
* a KMS key reference;
* an HMAC locator;
* plaintext answers belonging to another respondent.

---

## 5. Database responsibilities

### 5.1 Core database

The core database answers questions such as:

* Which published survey version is being completed?
* Was a survey link used?
* Is the link active and valid?
* Is this a fully anonymous respondent?
* Is the respondent associated with a project subject record?
* Is the session still in progress?
* When was the last activity?
* Has the session expired?
* Which questions were viewed?
* When was an answer saved?
* Has the respondent completed the session?

Relevant tables include:

```text
survey_links
project_subjects
project_subject_identities
project_subject_tokens
submission_sessions
submission_events
subject_ip_observations
survey_versions
```

The core database may store plaintext question-node IDs inside analytics events. This is useful for question-level analytics, but it is a deliberate metadata tradeoff. A conditional survey path can reveal limited information about the respondent even without storing the answer value.

`project_subjects` is the forward relation for project-scoped respondent
identity. Identity attachments, reusable subject-recognition tokens,
assigned-subject links, submission sessions, and IP observations stay in core
around that subject record. `submission_sessions.project_subject_id` may point
to it when access resolution identifies a known project participant. A null
`project_subject_id` means the session is fully anonymous at the core identity
layer. The response database stores opaque locators derived from the core
session UUID and the external linkage secret; it must not receive
project-subject IDs, identity IDs, user IDs, email addresses, IP addresses, or
recognition tokens. See [project-subjects.md](project-subjects.md) for the
relation boundary and
[subject-identity-and-access.md](subject-identity-and-access.md) for subject
resolution and identity-upgrade policy.

### 5.2 Response database

The response database answers questions such as:

* Which anonymous encrypted envelope belongs to this session locator?
* Which logical questions have saved answers?
* Which encrypted revision is currently canonical?
* What earlier encrypted revisions exist?
* Which wrapped DEK protects these rows?

Relevant tables include:

```text
response_envelopes
response_answers
response_answer_revisions
```

The response database does not know who the respondent is.

### 5.3 Relationship between the response tables

```text
response_envelopes
        │
        │ one envelope contains many logical answers
        ▼
response_answers
        │
        │ one logical answer contains many immutable revisions
        ▼
response_answer_revisions
```

The `response_answers` row is stable.

The `response_answer_revisions` rows are append-only.

The latest pointer moves forward as new revisions are inserted.

---
