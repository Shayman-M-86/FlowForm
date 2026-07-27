---
title: Security model
aliases: ["Security model"]
document_type: architecture
status: verified
authority: canonical
verified_evidence_digest: sha256:e57be9349fda451c912d3e14910cf141351529d9b6855a72f279e549a2030aae
last_edited: 2026-07-27
tags: [backend, infrastructure, security]
related_code:
  - "../../../backend/app/middleware/auth/"
  - "../../../backend/app/services/access/"
  - "../../../backend/app/services/public_submissions/"
  - "../../../backend/app/crypto/"
  - "../../../backend/app/core/config.py"
  - "../../../backend/app/middleware/rate_limit/"
  - "../../../infra/containers/"
  - "../../../infra/deployment/"
related_docs:
  - "Security knowledge"
  - "Trust boundaries"
  - "Identity and authentication"
  - "Respondent access and continuity"
  - "Responses and encryption"
  - "Configuration implementation"
---

# Security model

FlowForm separates operator access from respondent access, maps authenticated
external identities into local authorization state, hashes respondent session
and recognition credentials, and stores encrypted response values outside the
identity-bearing core store. Repository infrastructure also defines a public
proxy, private application role, constrained runtime containers, and secrets
delivery paths. These are controls visible in source and configuration, not a
claim that a live deployment has every declared control applied.

```text
operator browser -- Auth0 token --> backend authentication
                                         |
                                         v
                                  local authorization
                                         |
respondent browser -- link/cookie ------>+------> submission policy
                                         |
                         +---------------+---------------+
                         |                               |
                    Core store                    Response store
                identity + metadata             encrypted answers
                         \                               /
                          +------ trusted backend ------+
```

## Identity and authorization

Auth0 is the external identity provider for authenticated flows. Backend auth
middleware validates bearer credentials, while local users and access services
apply project and survey authorization. Public and link-based respondent access
uses a separate policy path; possession of an active survey-link credential can
grant the access allowed by its type and state. See [[identity-and-authentication|Identity
and authentication]] for the identity lifecycle and
[[respondent-access-and-continuity|Respondent access and continuity]] for the
product policy.

Respondent session and recognition credentials are represented by hashes in core
data and are returned to browsers as scoped cookies. Browser safety still needs
explicit review: cookie attributes and CORS handling are not a substitute for a
demonstrated CSRF policy, and deployment configuration determines the effective
origin boundary.

## Data, secrets, and runtime

Response values use a KMS-wrapped survey key, wrapped session keys, AES-GCM
payload encryption, and versioned opaque locators. The core and response stores
limit what either database contains alone, but the backend is a trusted
plaintext-handling point. [[responses-and-encryption|Responses and encryption]]
owns the detailed data model.

Configuration and bootstrap assets support file-backed secrets and separate
runtime configuration. Container and deployment definitions describe reduced
container privileges, read-only filesystems with temporary writable areas, a
reverse proxy, and restricted application connectivity. Their existence in the
repository does not establish deployed IAM, network, certificate, backup,
monitoring, or incident-response outcomes.

## Known limitations to retain during review

Rate limiting is application-local and depends on trusted client attribution.
Cross-store response operations are coordinated by the application rather than
by one transaction. Key material can be resident in worker memory. The
repository does not by itself establish governance for privileged users,
deployment-state verification, comprehensive endpoint authorization coverage,
or a complete threat model.

## Related documents

- [[security-index|Security knowledge]]
- [[trust-boundaries|Trust boundaries]]
- [[identity-and-authentication|Identity and authentication]]
- [[respondent-access-and-continuity|Respondent access and continuity]]
- [[responses-and-encryption|Responses and encryption]]
- [[configuration|Configuration implementation]]
