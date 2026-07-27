---
title: Security knowledge
aliases: ["Security knowledge"]
document_type: overview
status: verified
authority: canonical
verified_evidence_digest: sha256:2d6865b01232733ae5fd45c0875fb2e6d97618713567058dff409af88679cacb
last_edited: 2026-07-27
tags: [security]
related_code:
  - "../../../backend/app/middleware/auth/"
  - "../../../backend/app/crypto/"
  - "../../../backend/app/services/access/"
  - "../../../infra/containers/"
related_docs:
  - "Security model"
  - "Trust boundaries"
  - "Identity and authentication"
  - "Respondent access and continuity"
  - "Responses and encryption"
---

# Security knowledge

This branch explains the security-relevant responsibilities visible in the
repository: external identity verification, local authorization, respondent
access, response encryption, secrets use, and boundaries between browser,
services, infrastructure, and stores. It describes implementation and declared
infrastructure rather than certifying a deployed environment, compliance
programme, or complete threat model.

The security model gives the integrated control and limitation view. Trust
boundaries identify where authority or sensitive data crosses components and
what remains trusted at each crossing. Identity and authentication owns the
Auth0-to-local-user lifecycle. Data knowledge owns persistence and encrypted
responses. Product knowledge owns respondent link and continuity semantics.
This branch connects those responsibilities without duplicating their detailed
rules.

```text
browser / operator / respondent
              |
       identity or access proof
              |
              v
     backend policy boundary
       /        |         \
      v         v          v
 core data  response data  external key/secret services
      \         |          /
       +--------+---------+
                |
        deployment/runtime controls
```

## Related documents

- [[security-model|Security model]]
- [[trust-boundaries|Trust boundaries]]
- [[identity-and-authentication|Identity and authentication]]
- [[respondent-access-and-continuity|Respondent access and continuity]]
- [[responses-and-encryption|Responses and encryption]]
