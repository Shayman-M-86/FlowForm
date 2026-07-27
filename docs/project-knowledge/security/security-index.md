---
title: Security knowledge
aliases: ["Security knowledge"]
document_type: overview
status: draft
authority: canonical
verified_against_commit: null
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
responses, which this branch links to rather than duplicating.

## Related documents

- [[security-model|Security model]]
- [[trust-boundaries|Trust boundaries]]
- [[identity-and-authentication|Identity and authentication]]
- [[responses-and-encryption|Responses and encryption]]
