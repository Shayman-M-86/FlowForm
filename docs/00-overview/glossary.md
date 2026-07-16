---
title: Glossary
document_type: overview
status: draft
authority: canonical
verified_against_commit: ed0fb65df856e18807ee243b4bca512a8d0442b0
related_code:
  - "../../backend/app/schema/orm/core/"
  - "../../backend/app/schema/orm/response/"
  - "../../backend/app/services/public_submissions/"
  - "../../frontend/apps/studio-app/"
  - "../../frontend/apps/public-site/"
  - "../../infra/database/init/schema/flowform_core_db_schema_v4.sql"
  - "../../infra/database/init/schema/flowform_response_db_schema_v4.sql"
related_docs:
  - "System summary"
  - "Projects and access"
  - "Surveys and versioning"
  - "Links and subjects"
  - "Submissions"
  - "Responses and encryption"
  - "Frontend implementation"
---

# Glossary

Defines shared terms used across FlowForm documentation. These definitions name the current implementation without replacing the fuller domain explanations.

## Product structure

### Project

The top-level application scope for surveys, members and roles, subjects and participants, response-store configuration, and access rules. A project is persisted in `projects`; most records below it carry a `project_id`. See [[Projects and access]].

### Survey

A project-owned, durable survey container persisted in `surveys`. It carries identity and publication settings, including visibility, public slug, default response store, and the currently published version. Its editable or published content belongs to survey versions rather than directly to the survey. See [[Surveys and versioning]] and [[Builder and rules]].

### Survey version

A numbered snapshot within a survey, persisted in `survey_versions`. A version can be `draft`, `published`, or `archived`; published versions carry compiled survey schema. A submission session is pinned to one version so later survey editing does not silently change that attempt. See [[Surveys and versioning]].

## People and access

### Respondent

The person or browser acting through the respondent-facing API and form flow. `Respondent` is a role in routes and user-interface language, not a persisted entity type. Depending on access and recognition, a respondent's session can be associated with a subject, participant, authenticated user, or some combination of them. See [[Links and subjects]] and [[Submissions]].

### Subject

A stable, project-scoped record persisted in `project_subjects` and identified to users of the domain by a `subject_code`. Identities, recognition tokens, participants, and submission sessions can attach to it. A subject is broader than a participant: session-start resolution can create or recognize a subject that has no participant record. Subjects can also point to a canonical subject as aliases. See [[Links and subjects]] and [[Identity and authentication]].

### Participant

An enrolled project subject paired with one of that subject's identities. `project_participants` stores the subject and identity references, and database constraints require all three records to belong together in the same project. Assigned survey links reference a participant so the link reaches both a subject and an identity. A participant is therefore not the same thing as every respondent or every subject. See [[Links and subjects]].

### Survey link

A bearer-token access record persisted in `survey_links` for one survey. A link has a type (`general`, `private`, or `authenticated`), lifecycle fields, and an optional assigned participant. A participant assignment makes the link single-use in the current domain rules. This token is distinct from the browser submission-session token and the project subject-recognition token. See [[Links and subjects]] and [[Identity and authentication]].

## Submissions and responses

### Submission

The product-facing umbrella term for a respondent's survey attempt and its collected result. The current schema has no standalone `submissions` table; the attempt is represented primarily by a submission session, with core-side answer slots and events plus encrypted response-side data. See [[Submissions]].

### Submission session

One respondent attempt against an exact survey version, persisted in core data as `submission_sessions`. It records access and lifecycle metadata, the selected response store, and optionally a link and project subject; its state is `in_progress`, `completed`, or `abandoned`. A browser session token resumes commands for the current session, while opaque derived locators connect the session to response-side records without placing its core identifier in the response database. See [[Submissions]] and [[Responses and encryption]].

### Answer

The current respondent-provided state and value for one question in a submission session. `answered` and `cleared` are the supported states, while the value shape depends on the question family. The term describes the domain value; its core pointer and encrypted response-side storage are separate records. See [[Builder and rules]] and [[Responses and encryption]].

### Submission answer slot

The stable core-side pointer for one session-and-question pair, persisted in `submission_answer_slots`. It keeps question linkage and an optional question key, but not the plaintext answer. Its UUID is used to derive the opaque locator for the matching response answer. See [[Responses and encryption]].

### Response store

A project-scoped configuration record in `response_stores` describing a destination for response payloads. A survey selects a default store and a submission session records the selected store. The schema recognizes `platform_postgres` and `external_postgres`; the extent of runtime support for external stores remains an open question below. See [[Responses and encryption]] and [[Configuration implementation]].

### Response database

The separately mapped database that holds encrypted response envelopes and response answers. Its schema deliberately has no foreign keys to the core database and uses opaque, derived locators instead of project, survey, session, subject, user, or question identifiers. See [[Trust boundaries]] and [[Responses and encryption]].

### Response envelope

The anonymous response-side container for one submission session, persisted in `response_envelopes`. It is found by an opaque session locator and stores the wrapped session data-encryption key and crypto-version metadata; response answers are grouped beneath it. See [[Responses and encryption]].

### Response answer

The current encrypted response-side row for one submission answer slot, persisted in `response_answers`. It is keyed by an opaque answer locator and stores ciphertext, a nonce, and an optional client mutation identifier. The encrypted payload contains the real question identifier, answer state, and answer value. See [[Responses and encryption]].

## Applications

### Studio

The Vite and React application under `frontend/apps/studio-app`. Its protected `_studio` routes provide project, survey, builder, access, and results interfaces. The same application currently also contains the respondent route and `RespondPage`; “Studio” therefore does not describe every route shipped from this package. See [[Frontend implementation]].

### Public site

The Astro application under `frontend/apps/public-site`. Its current pages provide the public marketing home and documentation content. Despite its package name, it is not currently the application that implements the respondent survey route. See [[System context]] and [[Frontend implementation]].

## Open questions

- `external_postgres` is accepted in response-store metadata, but the inspected session flow receives one request-scoped response database session; dynamic external-store connection selection was not found and should not be claimed as operational without further implementation evidence.
- Product language does not yet establish whether “submission” should mean every attempt or only a completed attempt. Current code and permissions use the term broadly while persisting lifecycle state on `submission_sessions`.
- The intended long-term ownership of the respondent form between `studio-app` and `public-site` is not recorded by the inspected implementation. This glossary describes only the present placement.

## Related documents

- [[System summary]]
- [[Projects and access]]
- [[Surveys and versioning]]
- [[Links and subjects]]
- [[Submissions]]
- [[Responses and encryption]]
- [[Frontend implementation]]
