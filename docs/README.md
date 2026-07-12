---
title: FlowForm documentation home
document_type: overview
status: draft
authority: canonical
verified_against_commit: ed0fb65df856e18807ee243b4bca512a8d0442b0
tags: [meta]
related_code:
  - "../scripts/docs/"
related_docs:
  - "Documentation model"
  - "Documentation generator guide"
  - "Repository map"
  - "System summary"
---

# FlowForm documentation home

Entry point for the staged, partially verified FlowForm documentation.

## Documentation status

The documentation tree is being filled in stages and contains a mixture of draft, verified, and scaffold-only pages. A document's front matter states its authority and the commit used for verification. Until a claim has been checked against that commit's code, tests, configuration, CI, or infrastructure definitions, treat it as unverified.

## Layered structure

Documents are separated by purpose so that explanation, exact facts, temporary plans, and generated output do not compete as sources of truth. See the [[Documentation model|documentation model]] for the boundaries between layers and the [[Documentation generator guide|generator guide]] for the update process.

Documents reference each other with `[[wiki links]]` that resolve by front-matter title, carry their neighbours in `related_docs`, and use a small controlled tag vocabulary for cross-cutting classification. The [[Documentation model]] defines these knowledge-network conventions.

## Major sections

- [[System summary|00 Overview]]: project orientation, terminology, repository map, and documentation rules.
- [[System context|10 Architecture]]: system boundaries, runtime relationships, deployment shape, trust, and major data flows.
- [[Identity and authentication|20 Domains]]: product concepts, responsibilities, and invariants, one domain at a time.
- [[Local development|30 Workflows]]: verified end-to-end operational and development processes.
- [[Frontend implementation|40 Implementation]]: concise mappings from approved concepts and workflows to important code locations.
- [[Architecture decision records|50 Decisions]]: lasting architectural decisions whose rationale and consequences can be supported.
- [[Repository tree|60 Reference]]: exact, searchable repository facts and catalogues.
- [[Planning workspace|70 Planning]]: temporary plans, open work, and proposals that are not accepted architecture.
- [[Generated documentation|90 Generated]]: reproducible output with its generator and scanned sources identified.

## Suggested reading paths

For repository orientation, start with the [[Repository map|repository map]], then use the relevant reference catalogue. The system summary and later architecture, domain, workflow, and implementation documents remain future staged work and may still contain placeholders.

## Authority model

The implementation is the source of truth. Canonical documentation describes only implementation-backed current state. Reference documents hold exact facts without duplicating explanatory material. Planning documents are explicitly non-authoritative. Generated documents are authoritative only for the reproducible snapshot they declare and must not be edited by hand.

## Historical documentation

The `old-docs/` directory is historical and untrusted. It may provide ideas, but no claim from `old-docs/` is authoritative until re-verified against the implementation.
