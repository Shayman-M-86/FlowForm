---
title: Documentation system migration
aliases: ["Documentation system migration"]
document_type: historical-plan
status: draft
authority: historical
verified_against_commit: null
tags: [meta]
related_code: []
related_docs: ["Completed workspace material"]
---

# Documentation system migration

This is the completed migration manifest retained for historical accounting.
It records how the 75 version-one documents were assigned to the current
two-collection tree. It no longer governs documentation work; current agents
use the documentation model, authoring guide, and Docsys context workflow.

## Actions

- **move unchanged** — content is accurate as-is; move file, fix path-sensitive
  fields only.
- **move and verify** — move, then verify claims against code/tests/config and
  set `verified_against_commit` if verification occurred; otherwise
  `status: draft`/`scaffold` with `verified_against_commit: null`.
- **merge into another document** — fold content into a named destination that
  already owns the topic.
- **split into children** — promote to a folder with an index head plus child
  documents (only after debt analysis confirms multiple independent topics).
- **regenerate** — do not copy; the generator recreates it in the new tree.
- **archive** — move to `development-workspace/archive/` with minimal valid
  metadata; do not repair stale links.
- **do not migrate** — intentionally dropped (recorded with a reason).

`Verification` column: **Required** = must verify against implementation before
`verified`; **Planning only** = workspace material, honest incompleteness is
acceptable; **Generator-owned** = reproduced by tooling, never hand-authored.

## Collection mapping applied

| Legacy area | New destination |
| --- | --- |
| `00-overview/` | Project Knowledge branches; documentation governance → `engineering-practices/documentation/` |
| `10-architecture/` | Project Knowledge, grouped by primary subsystem |
| `20-domains/` | `product/`, `backend/`, `data/`, `security/` by owning subsystem |
| `30-workflows/` | `engineering-practices/`, `infrastructure/`, or `operations/` by ownership |
| `40-implementation/` | The subsystem branch that owns the implementation |
| `50-decisions/` | `development-workspace/decisions/` |
| `60-reference/` | `project-knowledge/reference/` |
| `70-planning/` | `development-workspace/planning/`, `technical-debt/`, or `archive/` |
| `90-generated/` | Regenerate under `project-knowledge/reference/generated/` |

## Manifest

### 00-overview/

| Legacy document | Destination | Action | Verification |
| --- | --- | --- | --- |
| `docs/00-overview/architecture-principles.md` | `project-knowledge/engineering-practices/documentation/architecture-principles.md` | move and verify | Required |
| `docs/00-overview/documentation-generator-guide.md` | `project-knowledge/engineering-practices/documentation/authoring-guide.md` | merge into another document | Required |
| `docs/00-overview/documentation-model.md` | `project-knowledge/engineering-practices/documentation/documentation-model.md` | move and verify | Required |
| `docs/00-overview/glossary.md` | `project-knowledge/reference/glossary.md` | move and verify | Required |
| `docs/00-overview/repository-map.md` | `project-knowledge/reference/repository-map.md` | move and verify | Required |
| `docs/00-overview/system-summary.md` | `project-knowledge/project-knowledge-index.md` | merge into another document | Required |
| `docs/README.md` | `docs-new-index.md` (root head; renamed to `docs-index.md` at cutover) | merge into another document | Required |

### 10-architecture/

| Legacy document | Destination | Action | Verification |
| --- | --- | --- | --- |
| `docs/10-architecture/component-map.md` | `project-knowledge/reference/component-map.md` | move and verify | Required |
| `docs/10-architecture/data-flows.md` | `project-knowledge/backend/data-flows.md` | move and verify | Required |
| `docs/10-architecture/deployment-model.md` | `project-knowledge/infrastructure/deployment/deployment-model.md` | move and verify | Required |
| `docs/10-architecture/runtime-containers.md` | `project-knowledge/infrastructure/containers/runtime-containers.md` | move and verify | Required |
| `docs/10-architecture/security-model.md` | `project-knowledge/security/security-model.md` | move and verify | Required |
| `docs/10-architecture/system-context.md` | `project-knowledge/project-knowledge-index.md` | merge into another document | Required |
| `docs/10-architecture/trust-boundaries.md` | `project-knowledge/security/trust-boundaries.md` | move and verify | Required |

### 20-domains/

| Legacy document | Destination | Action | Verification |
| --- | --- | --- | --- |
| `docs/20-domains/builder-and-rules.md` | `project-knowledge/product/builder-and-rules.md` | move and verify | Required |
| `docs/20-domains/identity-and-authentication.md` | `project-knowledge/security/identity-and-authentication.md` | move and verify | Required |
| `docs/20-domains/links-and-subjects.md` | `project-knowledge/backend/links-and-subjects.md` | move and verify | Required |
| `docs/20-domains/observability.md` | `project-knowledge/operations/observability.md` | move and verify | Required |
| `docs/20-domains/projects-and-access.md` | `project-knowledge/backend/projects-and-access.md` | move and verify | Required |
| `docs/20-domains/responses-and-encryption.md` | `project-knowledge/data/responses-and-encryption.md` | move and verify | Required |
| `docs/20-domains/submissions.md` | `project-knowledge/backend/submissions.md` | move and verify | Required |
| `docs/20-domains/surveys-and-versioning.md` | `project-knowledge/backend/surveys-and-versioning.md` | move and verify | Required |

### 30-workflows/

| Legacy document | Destination | Action | Verification |
| --- | --- | --- | --- |
| `docs/30-workflows/cloud-deployment.md` | `project-knowledge/infrastructure/deployment/cloud-deployment.md` | move and verify | Required |
| `docs/30-workflows/continuous-integration.md` | `project-knowledge/engineering-practices/continuous-integration.md` | move and verify | Required |
| `docs/30-workflows/database-migrations.md` | `project-knowledge/data/database-migrations.md` | move and verify | Required |
| `docs/30-workflows/local-development.md` | `project-knowledge/engineering-practices/local-development.md` | move and verify | Required |
| `docs/30-workflows/local-infrastructure.md` | `project-knowledge/infrastructure/local-infrastructure.md` | move and verify | Required |
| `docs/30-workflows/machine-image-building.md` | `project-knowledge/infrastructure/images/machine-image-building.md` | move and verify | Required |
| `docs/30-workflows/secrets-and-configuration.md` | `project-knowledge/infrastructure/secrets-and-configuration.md` | move and verify | Required |
| `docs/30-workflows/testing.md` | `project-knowledge/engineering-practices/testing.md` | move and verify | Required |

### 40-implementation/

| Legacy document | Destination | Action | Verification |
| --- | --- | --- | --- |
| `docs/40-implementation/backend.md` | `project-knowledge/backend/backend-index.md` | merge into another document | Required |
| `docs/40-implementation/backend/README.md` | `project-knowledge/backend/implementation/implementation-index.md` | move and verify | Required |
| `docs/40-implementation/backend/backend-configuration-patterns.md` | `project-knowledge/backend/implementation/backend-configuration-patterns.md` | move and verify | Required |
| `docs/40-implementation/backend/business-tracing.md` | `project-knowledge/operations/tracing/business-tracing.md` | move and verify | Required |
| `docs/40-implementation/backend/code-organization.md` | `project-knowledge/backend/implementation/code-organization.md` | move and verify | Required |
| `docs/40-implementation/backend/feature-slices.md` | `project-knowledge/backend/implementation/feature-slices.md` | move and verify | Required |
| `docs/40-implementation/ci-cd.md` | `project-knowledge/engineering-practices/ci-cd-implementation.md` | move and verify | Required |
| `docs/40-implementation/configuration.md` | `project-knowledge/infrastructure/configuration.md` | move and verify | Required |
| `docs/40-implementation/frontend.md` | `project-knowledge/frontend/frontend-index.md` | merge into another document | Required |
| `docs/40-implementation/infrastructure.md` | `project-knowledge/infrastructure/infrastructure-index.md` | merge into another document | Required |
| `docs/40-implementation/packer.md` | `project-knowledge/infrastructure/images/packer.md` | move and verify | Required |
| `docs/40-implementation/proxmox-rehearsal.md` | `project-knowledge/infrastructure/proxmox/proxmox-index.md` | merge into another document | Required |
| `docs/40-implementation/proxmox-rehearsal-fixtures.md` | `project-knowledge/infrastructure/proxmox/rehearsal-fixtures.md` | move and verify | Required |
| `docs/40-implementation/proxmox-rehearsal-observability.md` | `project-knowledge/infrastructure/proxmox/rehearsal-observability.md` | move and verify | Required |
| `docs/40-implementation/proxmox-rehearsal-setup.md` | `project-knowledge/infrastructure/proxmox/rehearsal-setup.md` | move and verify | Required |
| `docs/40-implementation/scripts.md` | `project-knowledge/reference/scripts-implementation.md` | move and verify | Required |

### 50-decisions/

| Legacy document | Destination | Action | Verification |
| --- | --- | --- | --- |
| `docs/50-decisions/0001-aws-staging-infrastructure-target.md` | `development-workspace/decisions/0001-aws-staging-infrastructure-target.md` | move unchanged | Planning only |
| `docs/50-decisions/ADR-template.md` | `development-workspace/decisions/adr-template.md` | move unchanged | Planning only |
| `docs/50-decisions/README.md` | `development-workspace/decisions/decisions-index.md` | merge into another document | Planning only |

### 60-reference/

| Legacy document | Destination | Action | Verification |
| --- | --- | --- | --- |
| `docs/60-reference/commands.md` | `project-knowledge/reference/commands.md` | move and verify | Required |
| `docs/60-reference/configuration-catalogue.md` | `project-knowledge/reference/configuration-catalogue.md` | move and verify | Required |
| `docs/60-reference/environment-variables.md` | `project-knowledge/reference/environment-variables.md` | move and verify | Required |
| `docs/60-reference/generated-files.md` | `project-knowledge/reference/generated-files.md` | move and verify | Required |
| `docs/60-reference/logging-schema.md` | `project-knowledge/reference/logging-schema.md` | move and verify | Required |
| `docs/60-reference/repository-tree.md` | `project-knowledge/reference/generated/repository-tree.md` | regenerate | Generator-owned |
| `docs/60-reference/scripts-catalogue.md` | `project-knowledge/reference/scripts-catalogue.md` | move and verify | Required |
| `docs/60-reference/services-and-ports.md` | `project-knowledge/reference/services-and-ports.md` | move and verify | Required |
| `docs/60-reference/tracing.md` | `project-knowledge/operations/tracing/tracing-index.md` | split into children | Required |

### 70-planning/

| Legacy document | Destination | Action | Verification |
| --- | --- | --- | --- |
| `docs/70-planning/README.md` | `development-workspace/planning/planning-index.md` | merge into another document | Planning only |
| `docs/70-planning/active/README.md` | `development-workspace/planning/planning-index.md` | merge into another document | Planning only |
| `docs/70-planning/active/aws-cdk-staging-plan.md` | `development-workspace/planning/aws-cdk-staging-plan.md` | move | Planning only |
| `docs/70-planning/active/docs-restructure-plan.md` | `development-workspace/planning/docs-restructure-plan.md` | move | Planning only |
| `docs/70-planning/completed/README.md` | `development-workspace/archive/archive-index.md` | merge into another document | Planning only |
| `docs/70-planning/completed/image-script-consolidation.md` | `development-workspace/archive/completed/image-script-consolidation.md` | move | Planning only |
| `docs/70-planning/abandoned/README.md` | `development-workspace/archive/archive-index.md` | merge into another document | Planning only |
| `docs/70-planning/abandoned/Security-review-1.md` | `development-workspace/archive/security-review-1.md` | archive | Planning only |
| `docs/70-planning/abandoned/Security-review-2.md` | `development-workspace/archive/security-review-2.md` | archive | Planning only |

### 90-generated/

All regenerated from the new tree; never copied. Destinations live under
`project-knowledge/reference/generated/`.

| Legacy document | Destination | Action | Verification |
| --- | --- | --- | --- |
| `docs/90-generated/README.md` | `project-knowledge/reference/generated/generated-index.md` | regenerate | Generator-owned |
| `docs/90-generated/api-routes.md` | `project-knowledge/reference/generated/api-routes.md` | regenerate | Generator-owned |
| `docs/90-generated/ci-workflows.md` | `project-knowledge/reference/generated/ci-workflows.md` | regenerate | Generator-owned |
| `docs/90-generated/configuration-index.md` | `project-knowledge/reference/generated/configuration-index.md` | regenerate | Generator-owned |
| `docs/90-generated/dependency-map.md` | `project-knowledge/reference/generated/dependency-map.md` | regenerate | Generator-owned |
| `docs/90-generated/documentation-dashboard.md` | `project-knowledge/reference/generated/documentation-dashboard.md` | regenerate | Generator-owned |
| `docs/90-generated/infrastructure-resources.md` | `project-knowledge/reference/generated/infrastructure-resources.md` | regenerate | Generator-owned |
| `docs/90-generated/repository-tree.md` | `project-knowledge/reference/generated/repository-tree.md` | regenerate | Generator-owned |

## Notes on judgment calls

- **`20-domains/` split by owning `related_code`:** identity/auth and
  trust/security material → `security/`; crypto and response-DB material →
  `data/`; survey/submission/link/project services → `backend/`; the survey
  *builder* (frontend `packages/builder`, rules) → `product/`. Observability is
  operational, so it and `business-tracing.md` → `operations/`.
- **Governance docs** (documentation model, generator guide, architecture
  principles) migrate first (Phase 4) into `engineering-practices/documentation/`.
  The generator guide **merges** into a single `authoring-guide.md` alongside the
  model rather than living as a separate near-duplicate.
- **`tracing.md` promotion:** the reference doc becomes the head of a
  `operations/tracing/` folder; `business-tracing.md` joins it as a child. Split
  only confirmed after `docsys debt --suggest-splits` (Phase 6, step 17).
- **`system-summary.md` / `system-context.md`** are folded into the Project
  Knowledge index head rather than kept as standalone overview pages, since the
  collection model expresses orientation through folder heads.
- **Two abandoned security reviews** are archived with minimal valid metadata;
  their 76 stale code-line links are **not** repaired (Phase 7, step 20).
- **Root `docs/README.md`** content folds into the root head, which is renamed
  `docs-index.md` at cutover (Phase 10, step 30).

## Migration progress

- **Bulk migration and acceptance — complete.** All 75 legacy inputs have a
  destination through move, merge, archive, or regeneration. The resulting
  91-document tree passes all five collection-validation profiles. Remaining
  implementation-backed pages stay `draft` with
  `verified_against_commit: null` until their claims receive focused review.

- **Phase 4 (governance) — done.** Built the real
  `project-knowledge/engineering-practices/documentation/` branch with four
  documents: `documentation-index.md` (head, title *Documentation practice*),
  `documentation-model.md`, `authoring-guide.md` (generator guide merged in),
  and `validation-and-review.md`. The legacy directory-layer table
  (`00-`/`10-`/… scheme) was intentionally dropped from the model — it describes
  the structure being migrated away from — and replaced by the two-collection
  description. `related_docs`/wiki-links were rewired to titles that already
  exist in the new tree.
- **Deferred from Phase 4 to Phase 6:** `glossary.md`, `repository-map.md`, and
  `architecture-principles.md`. Although governance-flavoured, each carries many
  `related_docs`/wiki-links to subsystem and domain documents that do not exist
  in the new tree until their branches migrate. Moving them now would strand a
  dozen cross-references and force a later rebuild, violating the "preserve
  titles / do not assume links survive" discipline. They migrate with
  `reference/` and the subsystem branches instead.
- **Phase 5 (Infrastructure pilot) — implementation complete; human gate
  pending.** Migrated all 13 Infrastructure inputs in this manifest and built a
  16-document branch comprising the shared head, substantive deployment,
  containers, images, and Proxmox branches, and three direct
  configuration/workflow pages. Implementation-backed pages were verified
  against `0edae9082dc3381cc1376e8a81276bf5c7bebf88`. Human review rejected
  taxonomy-only AWS, networking, and observability scaffolds: those concerns are
  now integrated into the overview that owns their current model and will gain
  child branches only when independently useful content exists. All validation
  profiles, deterministic Infrastructure search, advisory changed-document
  debt, docsys tests, image validation, and container invariant tests pass.
  The remaining human gate evaluates the revised overviews before Phase 6.

## Destination uniqueness check

Every one of the 75 legacy documents above appears exactly once. Rows whose
destination is a shared index head (`*-index.md`) use **merge**, not move, so no
two documents claim the same file as a move target.
