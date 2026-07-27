---
title: Projects and access
aliases: ["Projects and access"]
document_type: domain
status: draft
authority: canonical
verified_against_commit: null
tags: [backend, security]
related_code:
  - "../../../backend/app/services/access/"
  - "../../../backend/app/services/projects.py"
  - "../../../backend/app/services/members.py"
  - "../../../backend/app/services/roles.py"
  - "../../../backend/app/schema/orm/core/project.py"
  - "../../../backend/app/domain/permissions.py"
related_docs:
  - "Backend knowledge"
  - "Identity and authentication"
  - "Surveys and versioning"
  - "Security model"
---

# Projects and access

This draft describes the top-level collaboration scope used by Studio. A
project groups surveys, memberships, roles, subjects, response-store selection,
and administrative permissions. Authentication is separate, while respondent
survey-entry policy is owned by [[links-and-subjects|Links and subjects]].

The documented model uses project roles and named permissions for project work,
plus survey roles for survey-specific grants. Membership and role relationships
are expected to remain project-scoped; route-level access services calculate the
effective permission set before protected Studio operations proceed. Project
creation establishes the initial administrative relationship and a response
store context.

This page does not define survey versions, answer storage, or access tokens.
Those boundaries are described by [[surveys-and-versioning|Surveys and versioning]],
[[submissions|Submissions]], and the security branch. This page remains draft
until its claims are checked against a committed implementation baseline.

## Related documents

- [[backend-index|Backend knowledge]]
- [[surveys-and-versioning|Surveys and versioning]]
- [[links-and-subjects|Links and subjects]]
