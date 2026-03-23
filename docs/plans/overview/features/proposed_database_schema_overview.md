# Proposed Database Schema Overview

## Goal
Provide a clear and scalable database structure to support:
- project-based RBAC
- survey creation and management
- public and link-based survey access

This schema is designed to stay simple initially, while allowing future expansion.

---

# 1. Core Entities

## Users
Represents authenticated users from Auth0.

Key fields:
- auth0_user_id
- email
- display_name

---

## Projects
Top-level container for all work.

Key fields:
- name
- slug
- created_by

---

## Project Memberships
Links users to projects.

Key idea:
- one row per user per project

Responsibilities:
- tracks who belongs to a project
- stores membership state (active, invited, etc.)

---

# 2. RBAC (Roles & Permissions)

## Permissions
A fixed catalog defined by the system.

Examples:
- project.read
- project.update
- survey.create
- survey.update

Key idea:
- permissions are not user-defined

---

## Project Roles
Defined per project.

Examples:
- owner
- admin
- editor
- viewer

Key idea:
- each project can define its own roles

---

## Role → Permission Mapping

Project roles are linked to permissions.

Key idea:
- roles define capabilities
- permissions are reusable building blocks

---

## Membership → Role Assignment

Memberships are assigned one or more roles.

Key idea:
- users inherit permissions through roles

---

# 3. Surveys

## Surveys
Represents a questionnaire inside a project.

Key fields:
- project_id
- title
- status (draft, published, archived)
- visibility (private, link_only, public)

Key idea:
- surveys belong to a project
- visibility controls public access

---

## Survey Visibility Model

Three modes:

- private → only project members
- link_only → accessible via direct link
- public → accessible to anyone

Additional flags:
- allow_public_responses

---

# 4. Public Access

## Public Slug

Each survey can optionally have a public identifier.

Purpose:
- safe external URLs
- avoids exposing internal IDs

---

## Public Links (Optional)

Separate shareable links tied to a survey.

Capabilities:
- enable/disable access
- expire links
- control response permissions

---

# 5. Responses

## Survey Responses

Represents submitted answers to a survey.

Supports:
- authenticated submissions
- anonymous submissions
- tracking submission source (public link vs user)

---

# 6. Relationships Overview

High-level structure:

```
User → Membership → Project
                   ↓
                 Roles
                   ↓
              Permissions

Project → Surveys → Responses
                 ↓
           Public Access
```

---

# 7. Design Principles

### 1. Membership is the core
All project access flows through memberships.

### 2. Roles are flexible
Projects can define their own roles using a fixed permission set.

### 3. Permissions are controlled
Avoid dynamic or user-defined permission names.

### 4. Public access is separate
Handled through survey visibility and sharing, not roles.

### 5. Keep it minimal first
Start with:
- memberships
- project roles
- role-permission mapping
- surveys with visibility

Add advanced features later if needed.

---

# 8. Future Extensions

Only introduce when necessary:

- survey-specific roles
- fine-grained per-resource permissions
- organization-level grouping
- audit logs and access history

---

# Summary

This schema provides:
- clear separation of concerns
- flexible role management per project
- simple public access model for surveys

It is designed to be easy to reason about while supporting future growth.

