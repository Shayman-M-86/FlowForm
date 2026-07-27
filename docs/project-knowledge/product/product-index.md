---
title: Product knowledge
aliases: ["Product knowledge"]
document_type: overview
status: draft
authority: canonical
verified_evidence_digest: null
tags: [backend, frontend, security]
related_code:
  - "../../../frontend/packages/builder/src/"
  - "../../../backend/app/services/content.py"
  - "../../../backend/app/domain/submission_access_rules.py"
  - "../../../backend/app/services/public_submissions/"
related_docs:
  - "Builder and rules"
  - "Respondent access and continuity"
  - "Frontend implementation"
---

# Product knowledge

This branch owns user-facing concepts and rules that FlowForm implements.
Authors shape a versioned graph of questions and rules, while respondents reach
published content through visibility and link policies, establish continuity,
and complete a session against a frozen version. Product meaning here is
connected to, but distinct from, the frontend and backend components that
realize it.

```text
author intent --> draft survey --> published version
      |                |                  |
 questions + rules   builder UI       stable content
      \                |                  |
       +---------------+                  v
                                    access policy
                                          |
                                  subject continuity
                                          |
                                          v
                                  respondent journey
```

## Related documents

- [[builder-and-rules|Builder and rules]]
- [[respondent-access-and-continuity|Respondent access and continuity]]
- [[frontend-index|Frontend implementation]]
