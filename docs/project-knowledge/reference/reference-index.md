---
title: Reference documentation
aliases: ["Reference documentation"]
document_type: overview
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-08-03
tags: [meta]
related_code: []
change_triggers:
  - "../../../backend/"
  - "../../../frontend/"
  - "../../../infra/"
  - "../../../tools/"
related_docs:
  - "Glossary"
  - "Repository ownership and entry points"
  - "Component map"
---

# Reference documentation

This branch is the repository's orientation layer. It complements the domain,
architecture, and operations branches; it does not duplicate their workflows
or implementation detail.

Start with the [[glossary|Glossary]] for shared language and [[repository-map|
Repository ownership and entry points]] to find the area that owns a concern.
[[component-map|Component map]] gives the durable logical boundaries, while
[[technology-stack|Technology stack]] names the major technology families.
[[configuration-catalogue|Configuration and generated output]] explains how to
locate a setting or derived artifact without copying values, commands, or
machine-specific inventories. Reproducible detail belongs in the generated
reference branch.

```text
                         Reference documentation
                                   |
          +------------------------+------------------------+
          |                        |                        |
     orientation                ownership                 generated
 glossary / component map   repository / configuration  reproducible snapshots
       / stack                 and entry points          from repository sources
```

When reference entries conflict with code, tests, configuration, or regenerated
output, those implementation sources prevail. Authored entries remain draft
until checked against staged implementation evidence.

## Related documents

- [[glossary|Glossary]]
- [[repository-map|Repository map]]
- [[component-map|Component map]]
- [[technology-stack|Technology stack]]
- [[configuration-catalogue|Configuration and generated output]]
