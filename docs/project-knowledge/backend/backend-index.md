---
title: Backend knowledge
aliases: ["Backend knowledge"]
document_type: overview
status: draft
authority: canonical
verified_evidence_digest: null
tags: [backend]
related_code:
  - "../../../backend/app/"
  - "../../../backend/tests/"
related_docs:
  - "Data flows"
  - "Backend implementation documentation"
---

# Backend knowledge

This branch describes the Flask backend's domain responsibilities and the
implementation patterns used to change it. The backend accepts account, Studio,
respondent, and system requests, coordinates authorization and domain services,
and keeps core project metadata separate from encrypted response persistence.

The domain pages explain the lifecycle and ownership of projects, surveys,
respondent access, and submission attempts. The implementation branch explains
how those responsibilities are organised in code. Infrastructure configuration,
identity, cryptography, and generated API references are owned by their
respective branches; this branch links to them instead of duplicating their
details.

```text
Studio / respondent / system clients
                 |
                 v
        routes + API schemas
                 |
                 v
       authorization + services
             /          \
            v            v
       core metadata   response coordination
            |            |
            v            v
       Core store     Response store
```

Core and response stores are independent persistence boundaries. Consequently,
workflows that span them need explicit sequencing, compensation, or
reconciliation rather than a distributed database transaction. Pages remain
draft until their claims are checked against staged implementation evidence;
code and tests remain authoritative.

## Topics

- [[data-flows|Data flows]] traces the principal cross-boundary workflows.
- [[projects-and-access|Projects and access]], [[surveys-and-versioning|Surveys and versioning]],
  [[links-and-subjects|Links and subjects]], and [[submissions|Submissions]]
  describe the main backend domains.
- [[implementation-index|Backend implementation documentation]]
  describes code-level patterns.

## Related documents

- [[data-flows|Data flows]]
- [[implementation-index|Backend implementation documentation]]
