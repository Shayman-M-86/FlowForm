---
title: Reference documentation
aliases: ["Reference documentation"]
document_type: overview
status: verified
authority: canonical
verified_evidence_digest: sha256:0e56bffb4647b991f2856f38201bd9673d49a7ebe9ac090b7f683d8d5273f821
last_edited: 2026-07-28
tags: [meta]
related_code:
  - "../../../backend/"
  - "../../../frontend/"
  - "../../../infra/"
  - "../../../tools/docs/"
related_docs:
  - "Glossary"
  - "Repository map"
  - "Component map"
---

# Reference documentation

This branch is the repository's factual lookup layer. It complements the
explanatory Project Knowledge branches without replacing their ownership of
behaviour, architecture, or workflows. Use it to orient yourself, identify
exact locations and names, and find reproducible generated inventories.

The orientation set has three roles. [[glossary|Glossary]] stabilises shared
product and technical vocabulary; [[repository-map|Repository map]] gives a
maintained map from a responsibility to its repository area; and
[[component-map|Component map]] identifies the principal logical components and
their dependencies. [[technology-stack|Technology stack]] inventories the
languages, frameworks, services, and tooling each area depends on. Catalogue
pages provide exact commands, configuration, environment, ports, and scripts.
Generated pages are reproducible snapshots, not hand-authored authority.

```text
                         Reference documentation
                                   |
          +------------------------+------------------------+
          |                        |                        |
     orientation               catalogues               generated
 glossary / repo map     commands / config / ports    reproducible snapshots
   / component map         / scripts / variables      from repository sources
```

When reference entries conflict with code, tests, configuration, or regenerated
output, those implementation sources prevail. Authored entries remain draft
until checked against staged implementation evidence.

## Related documents

- [[glossary|Glossary]]
- [[repository-map|Repository map]]
- [[component-map|Component map]]
- [[technology-stack|Technology stack]]
