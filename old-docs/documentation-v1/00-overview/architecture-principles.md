---
title: Architecture principles
aliases:
  - "Architecture principles"
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
  - "../../infra/deployment/aws/cdk/"
  - "../../infra/database/init/schema/"
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
[[50-decisions/README|ADR index]] contains only a scaffold and template, so none of the observations below
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
See [[component-map|Component map]], [[backend|Backend implementation]], and
[[frontend|Frontend implementation]] for the detailed boundaries.

### Schema-derived consumer contracts

Backend API schemas feed the checked-in OpenAPI contract, from which repository
tooling derives frontend types, validation artifacts, constraints, and permission
metadata. Generated files are outputs rather than independent contract sources. See
[[generated-files|Generated files]] and [[frontend|Frontend implementation]] for ownership and regeneration details.

### Layered invariant enforcement

Application rules and database constraints both protect important state and
relationships. This overlap is observable for survey versioning and submission
data, but does not establish that every business rule has database enforcement;
domain-specific invariants belong
in pages such as [[surveys-and-versioning|Surveys and versioning]], [[projects-and-access|Projects and access]], and
[[submissions|Submissions]].

### Stable survey-version binding

Editing is restricted to draft survey versions, publishing records a compiled
schema, and collection records remain associated with the version used for the
attempt. The lifecycle, persistence enforcement, and remaining edge cases belong
in [[surveys-and-versioning|Surveys and versioning]] and [[data-flows|Data flows]].

### Separated identifying context and response payloads

Core storage owns application identities, survey structure, and submission
metadata; response storage holds anonymous encrypted response data. The stores
are connected by application-derived opaque locators rather than cross-database
foreign keys. This is an observed data-minimisation and trust-boundary pattern,
not a complete security claim. See
[[responses-and-encryption|Responses and encryption]], [[trust-boundaries|Trust boundaries]], and [[security-model|Security model]] for
the detailed model and unresolved risks.

### Explicit deployment and environment configuration

AWS resources are assembled as CDK stacks with declared dependencies, while a
typed environment configuration selects lifecycle safeguards, sizing, domains,
security scope, and whether a full cloud deployment is synthesized. Local and
cloud runtime paths are not identical, so portability or parity should not be
inferred from this pattern. See [[deployment-model|Deployment model]],
[[infrastructure|Infrastructure implementation]], and [[secrets-and-configuration|Secrets and configuration]] for operational detail.

## Knowledge boundaries and unresolved gaps

- No accepted ADR currently explains the rationale, required longevity, or
  permitted exceptions for these patterns.
- This pass verified representative source, schema, generation, and CDK paths;
  it did not prove uniform conformance across every route, service, frontend
  feature, workflow, or deployment resource.
- No atomic transaction spanning the two data stores was found; reconciliation
  and partial-failure behaviour require treatment in
  [[data-flows|Data flows]] and [[responses-and-encryption|Responses and encryption]].
- Security properties beyond the observed storage and encryption boundaries need
  threat-focused review in [[security-model|Security model]] and [[trust-boundaries|Trust boundaries]].
- If any observed pattern is intended to constrain future work, its rationale,
  alternatives, and consequences still need a reviewed ADR.

## Related documents

- [[system-context|System context]]
- [[component-map|Component map]]
- [[security-model|Security model]]
- [[surveys-and-versioning|Surveys and versioning]]
- [[responses-and-encryption|Responses and encryption]]
- [[50-decisions/README|Architecture decision records]]
- [[documentation-model|Documentation model]]
