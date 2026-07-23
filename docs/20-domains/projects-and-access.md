---
title: Projects and access
aliases:
  - "Projects and access"
document_type: domain
status: draft
authority: canonical
verified_against_commit: ad26b87e9820
tags: [security]
related_code:
  - "../../backend/app/services/access/"
  - "../../backend/app/services/projects.py"
  - "../../backend/app/services/members.py"
  - "../../backend/app/services/roles.py"
  - "../../backend/app/schema/orm/core/project.py"
  - "../../backend/app/domain/permissions.py"
related_docs:
  - "Identity and authentication"
  - "Surveys and versioning"
  - "Security model"
---

# Projects and access

Defines the top-level collaboration boundary and the role-based access model
used by Studio. Authentication is covered by
[[identity-and-authentication|Identity and authentication]]; respondent survey
access uses the separate model in [[links-and-subjects|Links and subjects]].

## Purpose

A project groups surveys, members, roles, subjects, response-store configuration,
and their administrative permissions. It is the tenant-like scope used to keep
records and authorization decisions from one project out of another.

## Responsibilities

- Create, list, read, update, and delete projects visible to an authenticated
  user through membership.
- Maintain project memberships, project roles, named permissions, and
  email-addressed invitations.
- Maintain project-scoped survey roles and assign at most one survey role to a
  project membership for a particular survey.
- Resolve effective project permissions from the member's project role and
  effective survey permissions from the union of project-role and survey-role
  grants.
- Enforce project and survey permission requirements at Studio route boundaries.
- Create every new project with an all-permissions system `Owner` role, an owner
  membership for the creator, and a primary platform response store.

## Non-responsibilities

- It does not authenticate credentials or issue bearer tokens.
- It does not decide whether a respondent link, public slug, or browser
  recognition token may start a submission.
- It does not own survey content/version transitions or encrypted answer data.
- A project role is an authorization grouping, not a global platform role;
  `platform_admin` is a separate user-level bypass in permission-decorated
  routes, not every membership-filtered list or read path.

## Main entities and invariants

| Entity | Role in the domain | Important invariant |
| --- | --- | --- |
| Project | Top-level scope with a unique slug | Creator may later be deleted because `created_by_user_id` is nullable. |
| Project role | Project-scoped named permission set | Role names are unique per project; system roles cannot be edited or deleted through the role service. |
| Project membership | One user in one project with an optional role and status | Unique per user/project; composite foreign keys keep an assigned role in the same project. |
| Project invitation | Pending or historical email invitation with a hashed token | Only one pending invitation per project/email; accepted records require actor and timestamp fields. |
| Survey role | Reusable project-scoped set of survey permissions | Contains only survey/submission permission names. |
| Survey membership role | Assignment of a survey role to a project membership | Primary key permits one assignment per survey/member; all referenced rows must share a project. |

Named permissions cover project administration, survey lifecycle actions, and
submission viewing. Permission rows are seeded at application startup. A
non-member has no effective permissions. A platform administrator bypasses the
project and survey permission decorators, while project listings and some
membership-derived reads remain filtered by local membership.

## Important workflows

1. Project creation writes the project, default response store, protected Owner
   role, and creator membership in one core transaction.
2. A protected Studio route authenticates the actor, resolves membership and
   role permissions for route identifiers, and applies its declared permission.
3. Survey authorization additionally looks up a survey-specific assignment and
   unions that role's permissions with the project-role grants.
4. Invitations are created and committed before email delivery. Acceptance
   checks the invitation and actor, creates a membership, and changes invitation
   state in one core transaction.
5. Member, role, and survey-role management remains scoped by composite keys and
   permission decorators even when numeric identifiers are supplied directly.

## Implementation map

- `backend/app/services/access/access_service.py` calculates effective access
  and supplies the project/survey route decorators.
- `backend/app/domain/permissions.py` is the application permission vocabulary;
  `backend/app/services/access/permissions_service.py` seeds it.
- `backend/app/services/projects.py`, `members.py`, `roles.py`,
  `survey_roles.py`, and `survey_members.py` own administrative use cases.
- `backend/app/repositories/access_repo.py` loads scoped membership and role
  relationships.
- `backend/app/schema/orm/core/project.py`, `survey_access.py`, and the core SQL
  schema encode same-project and uniqueness constraints.

## Verified gaps and open questions

- Access resolution currently ignores the membership `status`, so a membership
  marked `suspended` continues to receive its role permissions.
- A user in a custom role with `project:manage_roles` can add permissions to the
  same role. Survey-role assignment likewise has no self-assignment guard or
  actor permission ceiling. The intended delegation boundary is not documented.
- Invitation expiry is represented by `expires_at`, but creation and acceptance
  do not currently establish or enforce it.
- Invitation creation commits before sending email; there is no retry/outbox
  state for a delivery failure after the pending invitation becomes durable.
- Concurrent invitation acceptance relies on ordinary reads and a final commit,
  without row locking or a compare-and-set transition.
- Project and survey deletion currently commit only core-database cascades. The
  response-data retention/deletion contract is owned by
  [[responses-and-encryption|Responses and encryption]] and remains incomplete.

## Related documents

- [[identity-and-authentication|Identity and authentication]]
- [[surveys-and-versioning|Surveys and versioning]]
- [[security-model|Security model]]
