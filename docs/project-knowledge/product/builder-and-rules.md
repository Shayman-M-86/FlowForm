---
title: Builder and rules
aliases: ["Builder and rules"]
document_type: domain
status: draft
authority: canonical
verified_against_commit: null
tags: [frontend]
related_code:
  - "../../../frontend/packages/builder/src/"
  - "../../../frontend/packages/schema/src/generated/"
  - "../../../frontend/apps/studio-app/src/pages/SurveyWorkspaceTabPages/useSurveyBuilderController.ts"
  - "../../../frontend/apps/studio-app/src/pages/RespondPage.tsx"
  - "../../../backend/app/services/content.py"
  - "../../../backend/app/schema/api/requests/content/"
related_docs: ["Product knowledge", "Frontend implementation"]
---

# Builder and rules

Survey authoring represents a version as ordered question and rule nodes. The
shared builder package supports authoring and form-filling concerns, while the
Studio application coordinates saved draft state and the respondent page adapts
published content to submission commands. The browser's recovered draft is a
convenience copy; persisted version content remains the server-side record.

Question nodes express supported question families. Rule nodes evaluate
conditions and choose an outcome such as visibility/requiredness changes, a
jump, or termination. The form filler evaluates the resulting published graph
and controls respondent progress. Backend content services and request schemas
validate and persist version-scoped content, but frontend execution remains an
important part of the respondent rule behaviour.

```text
question nodes + rule nodes
            |
            v
      authored draft graph
            |
        publish/compile
            |
            v
     published runtime graph
            |
   +--------+---------+
   |                  |
show / require     jump / terminate
   |                  |
   +--------+---------+
            v
    respondent progress
```

Publishing and authorization are adjacent lifecycle boundaries rather than
responsibilities of the builder alone. The product also needs continued review
of graph validation, loop/missing-target handling, partial draft-save recovery,
and the contract that normalizes authored rule targets into published runtime
nodes.

## Related documents

- [[product-index|Product knowledge]]
- [[frontend-index|Frontend implementation]]
