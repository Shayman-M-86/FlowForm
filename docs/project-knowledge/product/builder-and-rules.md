---
title: Builder and rules
aliases: ["Builder and rules"]
document_type: domain
status: verified
authority: canonical
verified_evidence_digest: sha256:bcea33ef646985565b9631f2087f78e3e852ae8580bc9352c4eaa7e11c916bb0
last_edited: 2026-09-05
tags: [frontend]
related_code:
  - "../../../frontend/packages/builder/src/pages/builder/NodePage.tsx"
  - "../../../frontend/packages/builder/src/pages/builder/nodeFactories.ts"
  - "../../../frontend/packages/builder/src/pages/builder/ruleRelationships.ts"
  - "../../../frontend/packages/builder/src/components/form_filler/formFillerRuntime.ts"
  - "../../../frontend/packages/builder/src/components/form_filler/FormFiller.tsx"
  - "../../../frontend/apps/studio-app/src/pages/SurveyWorkspaceTabPages/useSurveyBuilderController.ts"
  - "../../../frontend/apps/studio-app/src/pages/RespondPage.tsx"
  - "../../../backend/app/services/surveys.py"
change_triggers:
  - "../../../frontend/packages/builder/src/"
  - "../../../frontend/packages/schema/src/generated/"
  - "../../../backend/app/schema/api/requests/content/"
related_docs: ["Product knowledge", "Frontend implementation", "Shared frontend packages", "Studio application", "Public Site application", "Surveys and versioning"]
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

## Authoring identity and state

Each node has a stable UUID identity, an editable `node_key` used by rule and
answer references, a sort key, a node type, and typed content. Choice options
and matching entries likewise keep identifiers separate from display labels.
Editing a label therefore does not inherently change the stored answer or rule
reference that uses its identifier.

The shared authoring component is controlled by its caller: nodes are the
definition state, while collapse, edit, and movement animation are local
presentation state keyed by stable node identity. Reorder controls are exposed
as labelled up/down buttons on desktop and mobile rather than requiring drag
alone. Studio owns server persistence and draft recovery; the Public Site demo
owns only browser-local state.

## Rule editing and execution

The editor derives earlier and later question sets for each rule. Conditions
are selected from earlier questions, while visibility/requiredness changes and
skip targets are selected from later questions. This directional authoring
model avoids introducing backward branches through the normal editor and gives
rules readable labels while storing `node_key` references.

The form-filler runtime separates stored answers from derived question
presentation state. It evaluates rules against answers, derives visibility and
requiredness, follows skips, and recognizes submit/discard outcomes. Missing
targets and excessive traversal are surfaced as invalid survey flows rather
than silently treated as successful completion.

```text
definition nodes + answer map + committed path
                    |
                    v
             rule evaluation
                    |
        +-----------+-----------+
        v           v           v
 visible/required  skip      submit/discard
        |
        v
 next effective question
```

The runtime retains navigation-time answers in component state, while the
completion result is assembled from the effective committed path. This should
not yet be read as a complete product policy for answers that become hidden
after earlier answers change; persistence and erasure semantics still require
an explicit cross-frontend/backend contract.

## Application adapters

The same portable components participate in three different contexts:

| Context | Adapter responsibility |
| --- | --- |
| Studio authoring | Load versioned nodes, recover unsaved drafts, check permissions, persist node diffs, and coordinate publish/archive actions. |
| Public Site demonstration | Keep a local browser draft and preview it without backend persistence. |
| Respondent route | Render a published compiled graph, save committed answers, and complete the backend submission session. |

Publishing and authorization are adjacent lifecycle boundaries rather than
responsibilities of the builder alone. The product still needs continued review
of reference repair after reorder/delete, complete graph validation, hidden
answer semantics, partial draft-save recovery, and the contract that normalizes
authored rule targets into published runtime nodes.

## Related documents

- [[product-index|Product knowledge]]
- [[frontend-index|Frontend implementation]]
- [[shared-frontend-packages|Shared frontend packages]]
- [[studio-application|Studio application]]
- [[public-site-application|Public Site application]]
- [[surveys-and-versioning|Surveys and versioning]]
