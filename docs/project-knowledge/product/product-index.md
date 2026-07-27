---
title: Product knowledge
aliases: ["Product knowledge"]
document_type: overview
status: draft
authority: canonical
verified_against_commit: null
tags: [frontend]
related_code:
  - "../../../frontend/packages/builder/src/"
  - "../../../backend/app/services/content.py"
related_docs: ["Builder and rules", "Frontend implementation"]
---

# Product knowledge

This branch owns user-facing concepts and rules that FlowForm implements. Its
first topic is survey building: authors shape a versioned graph of questions
and rules, while respondents traverse the published content through the shared
filler. Product meaning here is connected to, but distinct from, the frontend
component and API implementation that realizes it.

```text
author intent --> draft survey --> published version --> respondent journey
      |                |                  |                    |
 questions + rules   builder UI       stable content        form filler
      \                |                  |                    /
       +---------------+------------------+-------------------+
                               |
                         product behaviour
```

## Related documents

- [[builder-and-rules|Builder and rules]]
- [[frontend-index|Frontend implementation]]
