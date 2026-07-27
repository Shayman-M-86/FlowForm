---
title: Identity and authentication
aliases: ["Identity and authentication"]
document_type: domain
status: draft
authority: canonical
verified_against_commit: null
tags: [security]
related_code:
  - "../../../backend/app/middleware/auth/auth0.py"
  - "../../../backend/app/services/auth.py"
  - "../../../backend/app/services/account.py"
  - "../../../backend/app/schema/orm/core/user.py"
  - "../../../backend/tests/unit/test_auth_extension.py"
  - "../../../frontend/apps/studio-app/src/auth/passwordManagement.ts"
  - "../../../frontend/apps/studio-app/src/pages/AccountSettingsPage.tsx"
related_docs:
  - "Security knowledge"
  - "Security model"
  - "Trust boundaries"
---

# Identity and authentication

FlowForm uses Auth0 as its credential and login provider, then maps a verified
external subject to a local user record used by the application's access model.
This page owns that identity lifecycle. Project and survey permissions are a
separate authorization concern, and respondent recognition or survey links are
not substitutes for an Auth0 operator identity.

```text
Studio browser
      |
      v
Auth0 login --> bearer credential --> backend verification
                                          |
                                          v
                                local user resolution
                                          |
                                          v
                          project / survey authorization

respondent link or cookie --> separate respondent policy path
```

## Local identity boundary

Auth middleware extracts and validates bearer credentials for the configured
issuer and audience. Bootstrap code verifies the identity material needed to
create or resolve the local user, whose Auth0 subject is the stable login
identity. Core user data carries the fields needed for local account behaviour
and links to application access records; it is not intended to store Auth0
passwords, bearer tokens, ID tokens, MFA secrets, or Management API tokens.

Account services coordinate local profile and account changes with Auth0. The
Studio client has code for presenting password-management capability, including
the case where an external provider controls the credential. Those flows cross
an external service and local persistence, so they need recovery handling when
one side succeeds and the other does not.

## Boundaries and limitations

Authentication proves an external identity; it does not itself grant project or
survey access. Conversely, a respondent cookie, public survey, or survey-link
credential grants only the respondent behaviour allowed by its own policy. The
repository still needs explicit evidence for privileged-user grant/revocation,
recent-login or step-up requirements for sensitive actions, token/JWKS rotation
handling, and full recovery rules for Auth0-first account changes.

## Related documents

- [[security-index|Security knowledge]]
- [[security-model|Security model]]
- [[trust-boundaries|Trust boundaries]]
