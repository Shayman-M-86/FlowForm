# FlowForm Database Schema Overview

## Purpose

FlowForm uses **two separate PostgreSQL databases**:

1. **Core database**
   - Stores application data, users, projects, roles, permissions, survey definitions, publishing state, public links, response store configuration, and submission metadata.
   - Does **not** store raw survey answers.

2. **Response database**
   - Stores the actual submission payloads and answers.
   - Is designed so it can be either platform-managed or customer-managed.
   - Does not have foreign keys back to the core database.

This split is a deliberate architecture choice. It improves separation of concerns, supports stronger privacy boundaries, and makes customer-managed response storage possible.

---

## High-level Design

At a high level, the schema models this flow:

- A **user** belongs to a **project**.
- A project contains one or more **surveys**.
- A survey has one or more **survey versions**.
- A survey version is built from draft components such as:
  - questions
  - rules
  - scoring rules
- When a version is published, its **compiled_schema** becomes the frozen, authoritative artifact.
- Submissions are registered in the **core database**.
- Raw answers are stored in the **response database**.

This gives FlowForm a clean separation between:

- **application and governance data**
- **survey definition and publishing data**
- **sensitive submission payload data**

---

## Core Database Overview

### 1. Users and Projects

The core database begins with the basic application entities:

- `users`
- `projects`

A user is identified internally and also linked to Auth0 through `auth0_user_id`.
A project is the main container for surveys, roles, memberships, response stores, and pseudonymous subject mappings.

This makes the **project** the primary tenancy boundary.

---

### 2. Permissions and RBAC

The schema separates permissions from roles:

- `permissions`
- `project_roles`
- `project_role_permissions`
- `project_memberships`

This is a standard RBAC structure:

- permissions define what can be done
- roles collect permissions
- memberships assign a project role to a user within a project

There is also a second RBAC layer for survey-specific overrides:

- `survey_roles`
- `survey_role_permissions`
- `survey_membership_roles`

This means access can work in two levels:

- **project-level role** for general access
- **survey-level override role** for a specific survey

That is a strong design choice because it avoids forcing every permission decision into a single flat role model.

---

### 3. Response Store Configuration

The table `response_stores` defines where responses should be written.

This is important because the system supports both:

- platform-managed Postgres
- external/customer-managed Postgres

The schema stores a `connection_reference` JSONB object rather than raw credentials directly. That is a good security-oriented design because the application can reference secrets without making the database itself the source of secret truth.

A survey can point to a default response store with `default_response_store_id`, and composite foreign keys ensure the store belongs to the same project.

---

### 4. Surveys and Publishing

The publishing model is one of the strongest parts of the schema.

Relevant tables:

- `surveys`
- `survey_versions`
- `survey_questions`
- `survey_rules`
- `survey_scoring_rules`

#### Surveys
A survey belongs to a project and contains the high-level metadata:

- title
- visibility
- public response settings
- public slug
- default response store
- currently published version

The visibility rules are enforced with checks, so the database itself helps keep public/link-only behavior consistent.

#### Survey Versions
Each survey can have many versions. A version has:

- `version_number`
- `status`
- `compiled_schema`
- `published_at`
- soft delete support through `deleted_at`

Only `survey_versions` use soft delete. This is a thoughtful decision because old versions may still be required to correctly interpret historical answers.

#### Draft Components vs Published Artifact
The design clearly distinguishes between:

- **draft/build inputs**
  - questions
  - rules
  - scoring rules
- **published artifact**
  - `survey_versions.compiled_schema`

That means once a version is published, the compiled schema is treated as the frozen source of truth.

This is important because it avoids a common problem where historical submissions become hard to interpret after draft tables change.

---

### 5. Version Integrity Protections

The schema uses triggers and constraints to enforce publishing rules.

Important protections include:

- preventing changes to parts of a published version
- validating that `surveys.published_version_id` points to a real published version of the same survey
- preventing deletion or unpublishing of the active published version while it is still referenced
- automatically maintaining `updated_at`

This is a major strength of the design. The schema is not relying only on application code to preserve publishing correctness.

---

### 6. Public Access and Anonymous Response Support

The schema includes:

- `survey_public_links`
- `response_subject_mappings`

#### Public Links
Public survey access is handled with token prefixes and token hashes.
Only the hash is stored as the authoritative secret value.

That is the right direction for bearer-token style access because it avoids storing raw tokens in the database.

#### Pseudonymous Subjects
`response_subject_mappings` allows a real internal user to be represented by a stable pseudonymous UUID within a project.

This supports a privacy-preserving model where the response database can identify repeat subjects without storing their real user identity.

---

### 7. Submission Registry

The table `survey_submissions` is the bridge between the two databases.

It stores metadata such as:

- project
- survey
- survey version
- response store used
- submission channel
- submitting user or public link
- pseudonymous subject id
- external submission id
- submission status
- timestamps and delivery errors

This is a very important table architecturally.

It lets the core platform know:

- that a submission exists
- which survey version it belongs to
- where it was written
- whether delivery succeeded or failed

But it still keeps raw answers out of the core database.

The checks on this table are strong and deliberate. They enforce valid combinations for:

- authenticated submissions
- public-link submissions
- system submissions
- anonymous vs identified behavior

That helps prevent inconsistent submission states.

---

### 8. Audit Logging

The `audit_logs` table provides a general audit trail for actions on entities.

It is intentionally simple:

- who acted
- what action happened
- what entity type/id was affected
- metadata
- when it happened

This is a practical baseline for operational auditing.

---

## Response Database Overview

The response database is intentionally much smaller.

Relevant tables:

- `submissions`
- `submission_answers`
- `submission_events`

### 1. Submissions

The `submissions` table stores the submission header in the response database.
It includes:

- `core_submission_id`
- survey id
- survey version id
- project id
- pseudonymous subject id
- anonymity flag
- submitted time
- metadata

The key design detail here is that `core_submission_id` links back to `survey_submissions.id` in the core database, but there is no direct foreign key because the databases are separate.

That is the correct tradeoff for a split-database architecture.

---

### 2. Submission Answers

The `submission_answers` table stores one answer per question per submission:

- `question_key`
- `answer_family`
- `answer_value`

The schema uses JSONB for `answer_value` because different question families have different answer shapes.

Supported families are:

- `choice`
- `field`
- `matching`
- `rating`

The design is good because it balances:

- **relational structure** where it matters
- **JSON flexibility** where answer payloads vary

There are also helper functions and checks that validate the shape of each answer family at the database level.

Examples:

- choice answers must contain `selected_option_ids`
- field answers must contain a scalar `value`
- matching answers must contain structured `pairs`
- rating answers must contain numeric `value`

These checks are useful, but the schema correctly notes that backend validation against the frozen compiled schema is still the final authority.

---

### 3. Submission Events

The `submission_events` table is optional operational support.
It can record things such as:

- retries
- write failures
- delivery/debug events

This is helpful for asynchronous submission pipelines and troubleshooting.

---

## Key Structural Strengths

### Strong separation of concerns
The two-database split is clear and consistent.

### Good privacy posture
Sensitive answers are separated from application governance data.
Pseudonymous subject mapping supports anonymity and controlled re-identification boundaries.

### Strong publish/version model
The design treats the published compiled schema as authoritative and protects it from accidental mutation.

### Defensive integrity constraints
Composite foreign keys and check constraints help prevent cross-project and cross-survey mistakes.

### Flexible answer storage
JSONB answer payloads allow different question families without exploding the schema into too many narrow answer tables.

---

## Important Tradeoffs

### 1. JSONB is flexible, but backend validation is still essential
The response database validates shape, not full business meaning.
The application must still validate answers against the frozen compiled schema.

### 2. Separate databases reduce direct relational guarantees across boundaries
Because the response database is separate, cross-database integrity must be enforced by the application and write pipeline, not by SQL foreign keys.

### 3. Draft tables are build inputs, not historical truth
The schema is designed so published history should be interpreted from `compiled_schema`, not by reconstructing meaning from draft question/rule tables later.

This is the right choice, but it means the compile/publish pipeline becomes a critical application responsibility.

---

## Overall Assessment

This is a strong schema design.

The architecture is clearly aiming for:

- clean tenancy boundaries
- good RBAC structure
- controlled public sharing
- privacy-aware response handling
- publish-time freezing of survey structure
- compatibility with both platform-managed and customer-managed response storage

The most important idea in the whole design is this:

> the **core database governs the system**, while the **response database stores the sensitive answer payloads**.

That separation gives the system a solid foundation for privacy, scalability, and long-term maintainability.

---

## Short Mental Model

A simple way to think about the structure is:

- **Projects** own surveys and access control.
- **Surveys** own versions.
- **Versions** freeze the structure through `compiled_schema`.
- **Submissions** are registered in core.
- **Answers** are stored separately in the response database.
- **Pseudonymous IDs** allow privacy-preserving linkage when needed.

That is the core shape of the system.

