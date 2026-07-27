---
title: Component map
aliases: ["Component map"]
document_type: reference
status: draft
authority: canonical
verified_against_commit: null
tags: [backend, frontend, infrastructure, security]
related_code:
  - "../../../frontend/apps/"
  - "../../../frontend/packages/"
  - "../../../backend/app/core/factory.py"
  - "../../../backend/app/api/v1/"
  - "../../../backend/app/services/"
  - "../../../backend/app/repositories/"
  - "../../../backend/app/schema/orm/"
  - "../../../infra/database/init/schema/"
related_docs:
  - "Reference documentation"
  - "Data flows"
  - "Backend knowledge"
---

# Component map

This draft maps logical components and their principal dependencies. It stops
short of file-level ownership, sequence detail, and deployment topology.

| Component | Responsibility | Primary dependencies |
| --- | --- | --- |
| Public site | Static public product and documentation experience | shared frontend packages |
| Studio application | Project/survey management and respondent UI surface | Auth0, backend API, shared packages |
| Shared frontend packages | Builder, schema, UI, styles, and site-shell source shared by applications | generated backend contract where applicable |
| Backend API | HTTP boundary and coordination of auth, policy, persistence, encryption, and email | Auth0, service dependencies, core/response stores |
| Core data store | Identifying/admin state, survey content/access, and submission metadata | backend only |
| Response data store | Encrypted envelopes and answer rows, separate from core SQL relations | backend only |

```mermaid
flowchart TD
  PublicSite[Public site] --> Shared[Shared frontend packages]
  Studio[Studio application] --> Shared
  Studio -->|HTTP API| API[Flask backend]
  API --> Services[Services and policy]
  Services --> Core[(Core store)]
  Services --> Response[(Response store)]
  API <--> Auth0[Auth0]
```

The core and response stores are separate boundaries. Cross-store submission
work therefore needs explicit ordering and recovery logic, described in
[[data-flows|Data flows]]. The diagram is a logical dependency view, not a
guarantee of mechanically enforced layering or a deployment claim.

## Related documents

- [[reference-index|Reference documentation]]
- [[repository-map|Repository map]]
- [[data-flows|Data flows]]
