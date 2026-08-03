---
title: Product knowledge
aliases: ["Product knowledge"]
document_type: overview
status: verified
authority: canonical
verified_evidence_digest: sha256:ed613d280ffe3ca202beec2f62d24b1b5119786819fed51683d914e0f008647c
last_edited: 2026-08-04
tags: [backend, frontend, security]
related_code:
  - "../../../backend/app/services/content.py"
  - "../../../backend/app/domain/submission_access_rules.py"
change_triggers:
  - "../../../frontend/packages/builder/src/"
  - "../../../backend/app/services/public_submissions/"
related_docs:
  - "Builder and rules"
  - "Respondent access and continuity"
  - "Frontend implementation"
  - "Study interaction product direction"
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

## Current product boundary

The implemented product model covers survey authoring and publication,
respondent access and continuity, submission sessions, answer storage, and
result review. Its question-and-rule graph changes a respondent's path within a
survey through visibility, requiredness, jumps, and termination.

That graph is not a general model of the surrounding study or organisational
workflow. Participant records and assigned links support access and continuity;
they are not a case-management record for calls, appointments, lab work,
treatment, or analysis. Those activities may happen before, between, or after
FlowForm interactions without being represented inside the product.

[[study-interaction-product-direction|Study interaction product direction]]
explores a non-canonical product vision that builds on this boundary without
turning FlowForm into a complete research-operations system.

## Related documents

- [[builder-and-rules|Builder and rules]]
- [[respondent-access-and-continuity|Respondent access and continuity]]
- [[frontend-index|Frontend implementation]]
- [[study-interaction-product-direction|Study interaction product direction]]
