---
title: Architecture principles
document_type: overview
status: draft
authority: canonical
verified_against_commit: ed0fb65df856e18807ee243b4bca512a8d0442b0
tags: [backend, frontend, infrastructure, security]
related_code:
  - "../../backend/app/"
  - "../../backend/openapi.yaml"
  - "../../frontend/apps/"
  - "../../frontend/packages/"
  - "../../frontend/scripts/generate-types.mjs"
  - "../../infra/cdk/"
  - "../../infra/postgres/init/schema/"
related_docs:
  - "System context"
  - "Component map"
  - "Security model"
  - "Surveys and versioning"
  - "Responses and encryption"
  - "Architecture decision records"
  - "Documentation model"
---

# Architecture principles

Summarises high-level patterns observed across the current implementation. These
patterns describe the checkout at the verified commit; they are not substitutes
for accepted architectural decisions.

## Interpretation

FlowForm currently has no verified ADRs. The
[[Architecture decision records|ADR index]] contains only a scaffold and template, so none of the observations below
should be read as an approved, permanent constraint or as recovered design
rationale. A future ADR may adopt, change, or reject an observed pattern.

## Observed implementation patterns

### Explicit runtime responsibility boundaries

The backend separates HTTP routing, request and response schemas, service
orchestration, reusable domain rules, repositories, ORM models, and database
session management. The frontend similarly separates deployable applications
from workspace packages that supply shared survey, schema, shell, style, and UI
capabilities. This is an observed responsibility split, not a guarantee that
every module is equally thin or that dependencies are enforced mechanically.
See [[Component map]], [[Backend implementation]], and
[[Frontend implementation]] for the detailed boundaries.

### Schema-derived consumer contracts

Backend API schemas feed the checked-in OpenAPI contract, from which repository
tooling derives frontend types, validation artifacts, constraints, and permission
metadata. Generated files are outputs rather than independent contract sources. See
[[Generated files]] and [[Frontend implementation]] for ownership and regeneration details.

### Layered invariant enforcement

Application rules and database constraints both protect important state and
relationships. This overlap is observable for survey versioning and submission
data, but does not establish that every business rule has database enforcement;
domain-specific invariants belong
in pages such as [[Surveys and versioning]], [[Projects and access]], and
[[Submissions]].

### Stable survey-version binding

Editing is restricted to draft survey versions, publishing records a compiled
schema, and collection records remain associated with the version used for the
attempt. The lifecycle, persistence enforcement, and remaining edge cases belong
in [[Surveys and versioning]] and [[Data flows]].

### Separated identifying context and response payloads

Core storage owns application identities, survey structure, and submission
metadata; response storage holds anonymous encrypted response data. The stores
are connected by application-derived opaque locators rather than cross-database
foreign keys. This is an observed data-minimisation and trust-boundary pattern,
not a complete security claim. See
[[Responses and encryption]], [[Trust boundaries]], and [[Security model]] for
the detailed model and unresolved risks.

### Explicit deployment and environment configuration

AWS resources are assembled as CDK stacks with declared dependencies, while a
typed environment configuration selects lifecycle safeguards, sizing, domains,
security scope, and whether a full cloud deployment is synthesized. Local and
cloud runtime paths are not identical, so portability or parity should not be
inferred from this pattern. See [[Deployment model]],
[[Infrastructure implementation]], and [[Secrets and configuration]] for operational detail.

## Knowledge boundaries and unresolved gaps

- No accepted ADR currently explains the rationale, required longevity, or
  permitted exceptions for these patterns.
- This pass verified representative source, schema, generation, and CDK paths;
  it did not prove uniform conformance across every route, service, frontend
  feature, workflow, or deployment resource.
- No atomic transaction spanning the two data stores was found; reconciliation
  and partial-failure behaviour require treatment in
  [[Data flows]] and [[Responses and encryption]].
- Security properties beyond the observed storage and encryption boundaries need
  threat-focused review in [[Security model]] and [[Trust boundaries]].
- If any observed pattern is intended to constrain future work, its rationale,
  alternatives, and consequences still need a reviewed ADR.

## Related documents

- [[System context]]
- [[Component map]]
- [[Security model]]
- [[Surveys and versioning]]
- [[Responses and encryption]]
- [[Architecture decision records]]
- [[Documentation model]]
