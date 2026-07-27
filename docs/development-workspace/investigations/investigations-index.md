---
title: Engineering investigations
aliases: ["Engineering investigations"]
document_type: planning-index
status: draft
authority: working
verified_against_commit: null
tags: [meta]
related_code: []
related_docs: ["Development workspace"]
---

# Engineering investigations

Engineering investigations own bounded questions about observed behaviour,
risks, inconsistencies, or feasibility. They collect evidence, distinguish
findings from hypotheses, and leave unresolved points visible.

## Boundary

An investigation explains what was examined and what the evidence supports; it
does not itself accept a design, schedule work, or establish canonical system
truth. Use research for broader evidence gathering, experiments for controlled
trials, decisions for a choice, and technical debt for a known liability that
requires tracking.

## Lifecycle

Close an investigation with supported findings and a clear next state: no
action, further research or experiment, a decision, a plan, or a debt record.
Archive it once inactive while preserving the evidence boundary. Update Project
Knowledge separately if an accepted current-state claim is warranted.

```text
bounded question
      |
      v
inspect evidence --> findings --> no action / more research / experiment
                                      |          |             |
                                      +------> decision / plan / debt
                                                     |
                                             archive investigation
```

## Related documents

- [[development-workspace-index|Development workspace]]
- [[research-index|Engineering research]]
- [[experiments-index|Engineering experiments]]
- [[decisions-index|Engineering decisions]]
- [[technical-debt-index|Technical debt workspace]]
