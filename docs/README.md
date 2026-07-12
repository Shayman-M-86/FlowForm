---
title: FlowForm documentation home
document_type: overview
status: scaffold
authority: canonical
verified_against_commit: ac7d021ad3716a68638759df684b9a3c32bb4389
related_code: ["../scripts/docs/"]
related_docs:
  [
    "00-overview/documentation-model.md",
    "00-overview/documentation-generator-guide.md",
    "00-overview/repository-map.md",
  ]
---

# FlowForm documentation home

Entry point for the staged, partially verified FlowForm documentation.

## Documentation status

The documentation tree is being filled in stages and remains scaffold-status. A document's front matter states its authority and the commit used for verification. Until a claim has been checked against that commit's code, tests, configuration, CI, or infrastructure definitions, treat it as unverified.

## Layered structure

Documents are separated by purpose so that explanation, exact facts, temporary plans, and generated output do not compete as sources of truth. See the [documentation model](00-overview/documentation-model.md) for the boundaries between layers and the [generator guide](00-overview/documentation-generator-guide.md) for the update process.

## Major sections

- [00 Overview](00-overview/system-summary.md): project orientation, terminology, repository map, and documentation rules.
- [10 Architecture](10-architecture/system-context.md): system boundaries, runtime relationships, deployment shape, trust, and major data flows.
- [20 Domains](20-domains/identity-and-authentication.md): product concepts, responsibilities, and invariants, one domain at a time.
- [30 Workflows](30-workflows/local-development.md): verified end-to-end operational and development processes.
- [40 Implementation](40-implementation/frontend.md): concise mappings from approved concepts and workflows to important code locations.
- [50 Decisions](50-decisions/README.md): lasting architectural decisions whose rationale and consequences can be supported.
- [60 Reference](60-reference/repository-tree.md): exact, searchable repository facts and catalogues.
- [70 Planning](70-planning/README.md): temporary plans, open work, and proposals that are not accepted architecture.
- [90 Generated](90-generated/README.md): reproducible output with its generator and scanned sources identified.

## Suggested reading paths

For repository orientation, start with the [repository map](00-overview/repository-map.md), then use the relevant reference catalogue. The system summary and later architecture, domain, workflow, and implementation documents remain future staged work and may still contain placeholders.

## Authority model

The implementation is the source of truth. Canonical documentation describes only implementation-backed current state. Reference documents hold exact facts without duplicating explanatory material. Planning documents are explicitly non-authoritative. Generated documents are authoritative only for the reproducible snapshot they declare and must not be edited by hand.

## Historical documentation

The `old-docs/` directory is historical and untrusted. It may provide ideas, but no claim from `old-docs/` is authoritative until re-verified against the implementation.
