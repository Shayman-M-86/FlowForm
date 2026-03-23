# RBAC & Access Control Overview

## Goal
Provide a clear, scalable structure for authentication and authorization across the platform.

The system separates concerns into:
- Identity & API-level authorization (Auth0)
- Project-level RBAC (application database)
- Survey-level access & public sharing (application logic)

---

# 1. High-Level Architecture

```
[ Auth0 ] → [ API Layer ] → [ App RBAC ] → [ Resource Access ]
```

### Flow
1. User authenticates via Auth0
2. API validates JWT + permissions
3. App checks project membership + roles
4. App evaluates resource-specific rules (survey visibility, etc.)

---

# 2. Auth0 (Global / API-Level Authorization)

Auth0 is responsible for:
- Authentication (login, identity)
- Issuing JWT tokens
- Enforcing broad API permissions

### Auth0 Permissions (Coarse-Grained)
Examples:
- `project:read`
- `project:write`
- `project:admin`

These control **which API endpoints a user can call**, not specific resources.

### Auth0 Roles (Optional)
Examples:
- `platform_admin`
- `support_admin`
- `user`

These are **global roles**, not tied to specific projects.

### Key Rule
Auth0 answers:
> "Can this user call this type of endpoint?"

---

# 3. Application RBAC (Project-Level)

Handled entirely in the application database.

### Core Concept
Users belong to projects via memberships, and memberships have roles.

```
User → Membership → Project
                    ↓
                  Roles
                    ↓
               Permissions
```

---

## Project Roles

Defined per project.

Examples:
- `owner`
- `admin`
- `editor`
- `viewer`
- `survey_manager`

Project admins can:
- create roles
- assign permissions to roles
- assign roles to users

---

## Project Permissions (Fine-Grained)

Defined by developers as a fixed catalog.

Examples:
- `project.read`
- `project.update`
- `project.manage_members`
- `project.manage_roles`
- `survey.create`
- `survey.read`
- `survey.update`
- `survey.delete`
- `survey.publish`
- `response.read`

### Key Rule
Permissions are **not user-defined strings**.
They come from a controlled list.

---

## Role → Permission Mapping

Each role maps to a set of permissions.

Example:

```
owner:
  - all permissions

admin:
  - project.read
  - project.update
  - project.manage_members
  - survey.create
  - survey.update
  - survey.publish

editor:
  - survey.create
  - survey.read
  - survey.update

viewer:
  - project.read
  - survey.read
```

---

## Key Rule
Application RBAC answers:
> "Can this user perform this action on this project?"

---

# 4. Survey Access Model

Surveys introduce **public access + resource-specific behavior**.

This is separate from RBAC.

---

## Survey Visibility

Each survey has a visibility mode:

- `private` → only project members
- `link_only` → anyone with link
- `public` → anyone can discover and access

---

## Public Access Capabilities

Public users (non-members) may:
- view survey
- submit responses (if enabled)

Public users may NOT:
- edit surveys
- delete surveys
- manage roles

---

## Survey State

Surveys also have lifecycle state:

- `draft`
- `published`
- `archived`

### Rule
Public access is only allowed when:
- survey is `published`

---

## Public Sharing

Two approaches:

### 1. Slug-based access
- `/s/{public_slug}`

### 2. Share links (recommended)
- token-based links
- can expire
- can be revoked

---

## Key Rule
Survey access answers:
> "Can this request access this specific survey without authentication?"

---

# 5. Authorization Decision Flow

## Example: Edit Survey

1. Validate Auth0 token
2. Check Auth0 permission (`project:write`)
3. Load project membership
4. Resolve project roles
5. Check role → permission (`survey.update`)
6. Allow / deny

---

## Example: View Public Survey

1. Load survey
2. Check:
   - status = published
   - visibility = public OR link_only
3. Allow without authentication

---

## Example: Submit Response

Allow if:
- survey is published
- AND (
  - user has permission
  - OR public responses enabled
)

---

# 6. Design Principles

### 1. Separate concerns
- Auth0 → identity + API access
- DB → resource-level authorization

### 2. Roles over direct permissions
- assign roles to users
- assign permissions to roles

### 3. Keep permissions fixed
- avoid dynamic permission creation

### 4. Public access is NOT a role
- handled via visibility

### 5. Default + override model
- project roles = default
- survey visibility = override for public

---

# 7. Future Extensions

Add only if needed:

### Survey-specific roles
- per-survey editors/viewers

### Advanced sharing
- password-protected links
- expiring links

### Multi-tenant controls
- organization-level roles

---

# 8. Summary

- Auth0 controls **who can call your API**
- Project RBAC controls **what users can do in a project**
- Survey visibility controls **what the public can access**

This layered approach keeps the system:
- flexible
- secure
- easy to reason about

