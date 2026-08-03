# Project Membership & Two-Level RBAC (Project + Survey)

## The Two Levels

Access in Studio is resolved at two nested levels:

1. **Project membership** — a user joins a project with a base role (e.g.
   editor, owner) that grants a set of permissions across the whole project.
2. **Survey membership role** — within a survey, an existing project member
   can additionally be assigned a survey-specific role that grants extra
   permissions scoped to that one survey.

Survey-level access is never independent of project-level access: a survey
role can only be assigned to someone who is already a project member (it is
keyed off the project `membership_id`, not the user directly). There is no
such thing as survey-only membership.

---

## Resolution: Project First, Then Layered

`AccessService` resolves access in two steps:

- `get_project_access` loads the project membership and the permission set
  granted by its role.
- `get_survey_access` calls `get_project_access` first, then (if the user is
  a project member and the survey exists) looks up a survey-specific role
  assignment tied to that membership.

The **effective survey permission set is a union**: project-level
permissions plus survey-level permissions, not a replacement. This means a
survey role can only add permissions on top of the project role — it cannot
revoke or narrow what the project role already grants.

This is what enables cases like "Editor on Project X, but Owner on Survey Y
within X": the user keeps their project-level editor permissions everywhere,
and gains the additional owner-level permissions only on that one survey.

If the user has no project membership, survey access resolves to an empty
permission set — there's no fallback path that grants survey access without
project membership.

If the user is a project member but the survey does not exist, the current
`AccessService` implementation returns the project access plus an empty survey
layer. That means the effective permission set still contains the project-level
permissions. In practice, survey routes that load or mutate the survey should
still fail later on survey existence checks, but the permission resolution
object itself is not empty in this edge case.

---

## Enforcement

Permissions are enforced as flat string checks, not a role hierarchy:
`ensure_project_permission` / `ensure_survey_permission` simply check
membership exists, then check the requested permission string is present in
the resolved permission set. There's no concept of one role "outranking"
another at enforcement time — only whether a specific permission is in the
union.

Route-level enforcement happens via decorators
(`require_project_permission` / `require_survey_permission`) that resolve
access from route path parameters, enforce the permission, and cache the
resolved access object on the request context for reuse inside the view.

Platform admins bypass membership/permission resolution in the route
decorators. Direct permission-list endpoints such as `my-permissions` still call
`AccessService` and return whatever membership-derived permissions resolve for
that actor.

---

## Why This Shape

Without layering, supporting per-survey overrides would require either a
separate permission set for every (project role, survey role) combination,
or duplicating full role definitions at the survey level. Building survey
access as project access **plus** an additive survey layer avoids that
matrix, at the cost of survey roles only ever being able to grant, never
revoke, relative to the project role.

---

## Frontend

The frontend should not replicate this union logic. Its named permission hooks
call
`/projects/{project_id}/my-permissions` and
`/projects/{project_id}/surveys/{survey_id}/my-permissions`, which return the
already-resolved, already-merged permission list for the current user. Studio
hooks (`useProjectPermissions`, `useSurveyPermissions`) just check for
permission-string membership in that list — the project/survey merge is
entirely a backend concern.

Current Studio usage is mixed in a few survey leaf components: the survey
layout uses `useSurveyPermissions`, while some inner survey tabs still check
project permissions for survey actions. The hook contract above is the intended
shape for survey-scoped UI gating when survey-specific additive roles should be
honored.
