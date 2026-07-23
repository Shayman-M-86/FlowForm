---
title: FlowForm documentation home
aliases:
  - "FlowForm documentation home"
document_type: overview
status: draft
authority: canonical
verified_against_commit: ad26b87e9820
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

The documentation tree is being filled in stages and contains a mixture of concise implementation-backed drafts, independently verified pages, and generator-only scaffolds. A document's front matter states its authority and the commit used for verification. Until a claim has been checked against that commit's code, tests, configuration, CI, or infrastructure definitions, treat it as unverified.

## Layered structure

Documents are separated by purpose so that explanation, exact facts, temporary plans, and generated output do not compete as sources of truth. See the [[documentation-model|documentation model]] for the boundaries between layers and the [[documentation-generator-guide|generator guide]] for the update process.

Documents reference each other with Obsidian-compatible `[[note-filename|display title]]` links. Each note exposes its document title through an Obsidian `aliases` property, carries its neighbours by title in `related_docs`, and uses a small controlled tag vocabulary for cross-cutting classification. The [[documentation-model|Documentation model]] defines these knowledge-network conventions.

## Major sections

- [[system-summary|00 Overview]]: project orientation, terminology, repository map, and documentation rules.
- [[system-context|10 Architecture]]: system boundaries, runtime relationships, deployment shape, trust, and major data flows.
- [[identity-and-authentication|20 Domains]]: product concepts, responsibilities, and invariants, one domain at a time.
- [[local-development|30 Workflows]]: verified end-to-end operational and development processes.
- [[frontend|40 Implementation]]: concise mappings from approved concepts and workflows to important code locations.
- [[50-decisions/README|50 Decisions]]: lasting architectural decisions whose rationale and consequences can be supported.
- [[60-reference/repository-tree|60 Reference]]: exact, searchable repository facts and catalogues.
- [[70-planning/README|70 Planning]]: temporary plans, open work, and proposals that are not accepted architecture.
- [[90-generated/README|90 Generated]]: reproducible output with its generator and scanned sources identified.

## Suggested reading paths

For repository orientation, start with the [[repository-map|repository map]] and [[system-summary|system summary]], then follow the relevant architecture, domain, workflow, implementation, or reference page. Draft pages are intentionally concise and should be deepened only when the owning implementation is being reviewed. Some pages under [[90-generated/README|Generated documentation]] remain generator scaffolds until a reproducible generator is implemented.

## Authority model

The implementation is the source of truth. Canonical documentation describes only implementation-backed current state. Reference documents hold exact facts without duplicating explanatory material. Planning documents are explicitly non-authoritative. Generated documents are authoritative only for the reproducible snapshot they declare and must not be edited by hand.

## Historical documentation

The `old-docs/` directory is historical and untrusted. It may provide ideas, but no claim from `old-docs/` is authoritative until re-verified against the implementation.
