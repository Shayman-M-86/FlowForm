# FlowForm — V1 Rubric Plan

## Purpose
This document defines the **Version 1 scope** of FlowForm for the Udacity capstone project.

The goal of V1 is to:
- meet the rubric requirements
- keep the project realistically buildable in a limited time
- preserve the real long-term FlowForm concept
- produce a strong portfolio foundation that can continue after submission

V1 will focus on a **small but complete vertical slice** of the product.

---

## V1 Product Definition

FlowForm V1 will be a **dynamic form platform** where:
- an authenticated creator can create forms
- forms can contain questions and answer options
- forms can include simple conditional rules
- a respondent can complete the form through a guided flow
- submissions are stored in the database

The defining feature of V1 is:

**dynamic conditional questions powered by stored JSON rules**

---

## V1 Scope Strategy

The project will be intentionally split into two layers:

### 1. Capstone V1
A smaller version designed to satisfy the rubric and be completed in a reasonable timeframe.

### 2. Post-Capstone Expansion
A larger portfolio version that builds on the same architecture after submission.

This keeps the first release focused while preserving the larger product vision.

---

## What V1 Must Include

## 1. Backend API

The backend is the core of the capstone submission.

V1 must include:
- Flask API
- SQLAlchemy models
- PostgreSQL database
- relational schema for core application data
- JSON-based storage for rules
- RESTful CRUD endpoints
- JSON error responses
- authentication and RBAC with Auth0
- automated tests
- live deployment

---

## 2. Core Data Model

V1 should keep the data model simple and structured.

Recommended core entities:
- **Form**
- **Question**
- **AnswerOption**
- **FormRule**
- **Submission**
- **Response**

### Data Modeling Direction
- Use a relational schema for forms, questions, answer options, submissions, and responses.
- Store conditional rule definitions in JSON or JSONB.
- Keep model helper methods for insert, update, delete, and serialization.

This matches the long-term architecture while keeping the implementation manageable.

---

## 3. Rule Engine Scope for V1

The rule engine must be intentionally limited.

### Initial Rule Goal
Only implement enough dynamic behaviour to clearly prove the FlowForm concept.

### Recommended V1 Rule Features
**Trigger**
- `on_answer`

**Condition operators**
- `equals`
- `not_equals`
- optional: `contains`

**Actions**
- `show_question`
- `hide_question`
- optional: `end_form`

### Important Constraint
Do **not** build a large generic rule engine for V1.

The goal is simply to show that the form can change dynamically based on previous answers.

---

## 4. Authentication and RBAC

V1 must satisfy the rubric requirements for Auth0 and role-based access control.

### Authentication
- Auth0
- OAuth 2.0 Authorization Code Grant with PKCE
- OpenID Connect

### Required RBAC Structure
At least **two roles** with clearly different permissions.

Recommended roles:

### Creator
- create forms
- edit forms
- delete forms
- view submissions

### Participant
- view published forms
- submit responses

This keeps RBAC meaningful while still being simple enough for V1.

---

## 5. API Scope for V1

The API should be designed around the rubric requirements and the core FlowForm workflow.

### Recommended Endpoints

#### GET
- `GET /forms`
- `GET /forms/<id>`
- `GET /forms/<id>/submissions`

#### POST
- `POST /forms`
- `POST /forms/<id>/questions`
- `POST /forms/<id>/submit`

#### PATCH
- `PATCH /forms/<id>`
- `PATCH /questions/<id>`

#### DELETE
- `DELETE /forms/<id>`
- optional: `DELETE /questions/<id>`

### Error Handling
Return JSON errors for at least four status codes, such as:
- 400
- 401
- 404
- 422

---

## 6. Frontend Scope for V1

The frontend should remain **very small**.

It should be a **React single page application**, but only include enough interface to demonstrate the product and support the capstone submission.

### Frontend Goals
- Auth0 login redirect
- basic authenticated user experience
- simple form list page
- simple form detail page
- simple form creation or question creation screen
- minimal respondent form fill flow

### Important Constraint
The frontend is **not** the main focus of V1.

It should support the backend and demonstrate the concept, but it should not become a major source of scope expansion.

---

## 7. Hosting for V1

For the long-term version of FlowForm, the planned hosting stack is:
- React SPA on S3 + CloudFront
- Flask API on ECS Fargate
- PostgreSQL on RDS
- Auth0 outside AWS

For the capstone submission, deployment should be chosen based on **submission certainty first**.

### V1 Hosting Priority
- deploy the API live
- make authentication testable
- keep deployment reliable

If full AWS deployment is realistic within the timeframe, use it.
If deployment becomes a blocker, simplify deployment for submission and move the full AWS target into the next phase.

---

## Rubric Mapping

## Data Modeling
V1 will satisfy this by:
- defining relational SQLAlchemy models
- using proper field types and keys
- using model helper methods
- using SQLAlchemy queries instead of raw SQL
- serializing model data for API responses

## API Architecture
V1 will satisfy this by:
- using RESTful endpoints
- implementing GET, POST, PATCH, and DELETE
- supporting CRUD behaviour
- returning JSON error responses

## Authentication and RBAC
V1 will satisfy this by:
- using Auth0
- implementing a custom `@requires_auth` decorator
- validating JWTs
- enforcing permission-based access control
- defining at least two roles with distinct permissions

## Testing
V1 will satisfy this by:
- adding success and failure tests for each endpoint
- adding RBAC tests for each role
- validating expected API behaviour with unittest

## Deployment
V1 will satisfy this by:
- hosting the API live
- documenting the live URL in the README
- documenting authentication setup for reviewers

## Documentation and Code Quality
V1 will satisfy this by:
- using PEP 8 style
- keeping code organized and DRY
- storing secrets in environment variables
- documenting setup, dependencies, endpoints, and RBAC in the README

---

## What to Leave for Later

The following features should be postponed until after submission unless the core version is already complete:
- advanced scoring engine
- visual rule builder
- analytics dashboard
- complex branching combinations
- multi-page form builder
- advanced admin features
- multi-tenant support
- advanced audit tooling
- richer frontend design system
- more complex infrastructure automation

---

## Development Roadmap for V1

## Phase 1 — Project Skeleton
Build the project foundation first.

### Deliverables
- repository structure
- Flask app setup
- PostgreSQL connection
- SQLAlchemy base models
- React SPA scaffold
- Auth0 tenant and API setup
- environment variable setup

### Phase 2 — Core Data Model and CRUD

Build the relational model before the dynamic logic.

### Deliverables

- Form model
- Question model
- AnswerOption model
- FormRule model
- Submission model
- Response model
- database schema migrations (Alembic)
- migration workflow for schema evolution
- CRUD endpoints for forms and questions

### Migration Guidance

Use **Alembic** with SQLAlchemy to manage schema changes during development.

This ensures the database schema can evolve safely as the project grows beyond V1.

## Phase 3 — Authentication and RBAC
Add security early so protected endpoints are designed correctly.

### Deliverables
- custom `@requires_auth` decorator
- JWT validation
- Auth0 permissions setup
- Creator and Participant roles
- protected endpoints

## Phase 4 — Rule Engine V1
Add the smallest possible dynamic rule behaviour.

### Deliverables
- JSON rule schema for V1
- rule parsing and validation
- `on_answer` trigger support
- `show_question` and `hide_question` actions
- simple rule evaluation in submission flow

## Phase 5 — Submission Flow
Build the main product workflow.

### Deliverables
- start form submission
- submit answers
- evaluate next visible questions
- store submission and responses

## Phase 6 — Minimal Frontend
Only after the backend workflow exists.

### Deliverables
- login page or login button
- basic form list screen
- basic form detail screen
- minimal form creation interface
- minimal form completion flow

## Phase 7 — Testing and Documentation
Stabilize the project before deployment.

### Deliverables
- endpoint tests
- RBAC tests
- README
- endpoint documentation
- role and permission documentation
- local setup instructions
- reviewer authentication instructions

## Phase 8 — Deployment
Deploy only after the core workflow is stable.

### Deliverables
- live hosted API
- working Auth0 configuration
- public URL in README
- final environment configuration

---

## Recommended Build Order

If time is limited, build in this order:

1. backend project skeleton
2. relational data model
3. core CRUD endpoints
4. Auth0 and RBAC
5. rule engine V1
6. submission flow
7. tests
8. deployment
9. very small SPA frontend

This order keeps the rubric-critical parts first.

---

## Small Frontend Recommendation

The React SPA for V1 should stay intentionally narrow.

Recommended pages or views:
- login / logout
- form list
- form detail
- create form
- complete form

Keep styling simple.
Keep component count small.
Avoid advanced state management unless clearly needed.

The backend and dynamic form behaviour should remain the priority.

---

## Post-Capstone Roadmap

After submission, FlowForm can expand into the larger portfolio version.

### Next likely improvements
- richer rule engine
- visual logic builder
- quiz scoring
- analytics dashboard
- better UI and UX
- stronger AWS deployment maturity
- CI/CD improvements
- versioning for forms and rules
- audit logging

---

## Summary

FlowForm V1 should be treated as a **focused capstone release**, not the full final product.

The strongest approach is to build:
- a solid backend API
- a limited but real dynamic rule engine
- Auth0 RBAC
- automated tests
- live deployment
- a very small React SPA that proves the concept

This gives you the best chance of finishing the capstone well while still laying the foundation for a serious long-term portfolio project.

