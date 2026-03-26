# FlowForm

FlowForm is a dynamic form platform for building interactive surveys, questionnaires, and quizzes that adapt in real time based on user input.

Unlike traditional static forms, FlowForm allows creators to define conditional logic so that questions can appear, disappear, or change depending on previous answers. This creates a guided experience where users only see questions that are relevant to them.

## Core Idea

FlowForm is built around three key concepts:

- **Structure** – forms are composed of questions and answer options
- **Logic** – rules define how the form changes based on responses
- **Execution** – the form dynamically updates as users interact with it

This enables features such as:

- conditional question flow
- skipping irrelevant sections
- branching logic
- decision-based questionnaires

## Architecture

FlowForm is designed as a modern full-stack web application:

- **Frontend:** React single-page application
- **Backend:** Flask API with Python
- **Database:** PostgreSQL with a hybrid relational + JSON model

The system uses a relational schema for core entities (forms, questions, submissions) while storing flexible rule definitions and response payloads as JSON.

## Key Features

- Dynamic forms powered by rule-based logic
- RESTful API for form management and submissions
- Role-based access control (RBAC)
- Secure authentication using Auth0 (OAuth 2.0 + OIDC)
- Separation of application data and response data for privacy
- Versioned forms with immutable published schemas

## Data Model Highlights

- **Forms and Questions** are stored relationally
- **Rules** are stored as JSON for flexibility
- **Responses** are stored separately from core application data
- **Question families** (choice, field, matching, rating) provide structured flexibility

This approach balances strong data integrity with the flexibility required for dynamic form behaviour.

## Security

FlowForm uses a modern authentication architecture:

- OAuth 2.0 Authorization Code Flow with PKCE
- OpenID Connect (OIDC)
- Auth0 as the identity provider
- JWT-based API authentication
- Refresh token rotation for secure session handling

Authorization is handled through a layered RBAC system:

- Auth0 controls API-level access
- Application roles control project-level permissions
- Survey visibility controls public access

## Infrastructure

The planned deployment architecture uses AWS:

- **Frontend:** S3 + CloudFront
- **Backend:** ECS Fargate (Docker containers)
- **Database:** Amazon RDS (PostgreSQL)
- **Authentication:** Auth0 (external)

This provides a production-style, scalable foundation while remaining cost-effective.

## Project Scope (V1)

The initial version focuses on a complete vertical slice of the product:

- Create and manage forms
- Define basic conditional logic
- Submit and store responses
- Authenticate users and enforce RBAC
- Provide a minimal frontend to demonstrate the flow

The goal of V1 is to deliver a working system that proves the core concept while keeping the scope manageable.

## Vision

FlowForm aims to make it easy to build intelligent, adaptive forms that improve user experience and data quality.

Future versions may include:

- visual rule builders
- advanced scoring systems
- analytics dashboards
- more complex branching logic

---

FlowForm is designed as both a practical application and a production-style backend project, focusing on clean architecture, security, and scalability.

---

### Development Quick Start

```bash
git clone https://github.com/Shayman-M-86/FlowForm.git
cd FlowForm
code .vscode/flowform.code-workspace
```

### Setup

Allow automatic tasks when prompted.

If it doesn’t run:

- Press `Ctrl + Shift + B` to run `Build Task`

---

### Package Management

This project uses uv for dependency management.

- Do not use `pip` directly
- Use `uv` commands for installing and syncing dependencies

[UV Python package manager](https://github.com/astral-sh/uv)

---

### Workspace

This is a **multi-root workspace**:

- `root` → entire repository
- `backend` → backend only
- `frontend` → frontend only

You can:

- Work from **root** for the full project
- Work from **backend** if focusing on API development

---

### Recommended Extensions

- ms-python.python
- ms-python.vscode-pylance
- charliermarsh.ruff
- ms-python.black-formatter

---

#### Note

If tasks were blocked:

`Ctrl + Shift + P` → `Tasks: Manage Automatic Tasks` → Allow
