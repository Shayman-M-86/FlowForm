# FlowForm Database Schema – Design Overview

## Purpose
This schema is designed to support a flexible, secure, and scalable survey platform.

It is split into two databases:
- **Core Database** → stores structure, users, permissions, and survey definitions
- **Response Database** → stores submitted answers only

This separation improves:
- security (responses can be isolated)
- scalability (responses grow independently)
- flexibility (supports platform-managed or customer-managed storage)

---

## Core Design Principles

### 1. Strict Context Integrity
All relationships are constrained so that data cannot cross project or survey boundaries.

Examples:
- roles must belong to the same project as memberships
- survey versions must belong to the same survey
- response stores must belong to the same project

This prevents subtle data corruption and enforces correctness at the database level.

---

### 2. Hard Deletes for Most Entities
Most entities are **fully deleted**, not soft deleted.

This keeps the system simple and avoids:
- stale unique constraints
- hidden or confusing "deleted" data

Entities using hard deletes include:
- projects
- surveys
- memberships
- roles
- response stores

---

### 3. Soft Delete Only for Survey Versions
`survey_versions` are the only soft-deleted entity.

Reason:
- they contain the exact schema used to collect responses
- responses must always be interpretable using the original schema

Deleting a version should not break historical data.

---

### 4. Versioned Survey Model
Surveys are versioned instead of overwritten.

Each version contains:
- compiled schema (questions, structure)
- rules and scoring
- publication state

This allows:
- safe updates
- historical consistency
- reproducible submissions

---

### 5. Decoupled Response Storage
Responses are stored in a separate database with no foreign keys to the core database.

Instead, they reference:
- `core_submission_id`

This allows:
- independent scaling
- external/customer-managed storage
- reduced blast radius for sensitive data

---

### 6. Pseudonymous Identity Mapping
User identity is separated from response data using:
- `response_subject_mappings`

This provides:
- anonymity at the response layer
- optional traceability at the project level

---

### 7. Flexible Answer Storage (JSONB)
Answers are stored as JSON to support multiple question types.

Examples:
- choice
- rating
- free text

Validation is handled at the application layer to keep the schema flexible.

---

### 8. Role-Based Access Control (RBAC)
The system uses a layered RBAC model:

- **Project roles** → global access within a project
- **Survey roles** → optional overrides per survey

Permissions are normalized and reusable.

---

### 9. Public Access Model
Surveys can be accessed via:
- public slug
- generated public links (token-based)

This supports:
- open surveys
- restricted link-based distribution

---

### 10. Submission Registry Pattern
The core database stores submission metadata:
- submission ID
- survey + version
- response store location

The actual answers live in the response database.

This acts as a routing and tracking layer between systems.

---

## Summary

This schema prioritizes:
- data integrity (strict relational constraints)
- security (separation of concerns)
- flexibility (JSON + versioning)
- scalability (split databases)

It is designed to support both simple survey use cases and more advanced, enterprise-level configurations without requiring structural changes.

