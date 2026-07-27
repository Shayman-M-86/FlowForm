---
title: Product knowledge
aliases: ["Product knowledge"]
document_type: overview
status: verified
authority: canonical
verified_evidence_digest: sha256:03a269819498fc21b450d2f60b04c2801e56334a4a76d431ba4c7922624fdf58
last_edited: 2026-07-27
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
