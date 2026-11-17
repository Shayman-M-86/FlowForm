---
title: Backend implementation guides
aliases:
  - "Backend implementation guides"
document_type: implementation
status: draft
authority: canonical
verified_against_commit: cd9bd50
tags: [backend]
related_code:
  - "../../../backend/app/"
  - "../../../backend/tests/"
related_docs:
  - "Backend implementation"
  - "Testing workflow"
  - "Database migrations"
---

# Backend implementation guides

Provides construction-level guidance for changing the Flask backend. These
guides describe patterns observed in the current implementation; the code and
tests remain authoritative when a guide and a local feature differ.

## Use this area

Start with [[backend|Backend implementation]] for the broad ownership map, then
use one focused guide while making a change:

| Guide | Use it when |
| --- | --- |
| [[code-organization|Backend code organization]] | deciding where a new module belongs or what it may depend on |
| [[feature-slices|Backend feature slices]] | adding or changing an endpoint, use case, persistence operation, or API contract |
| [[backend-configuration-patterns|Backend configuration patterns]] | adding a runtime setting, secret, environment variable, or startup validation |
| [[business-tracing|Business tracing]] | adding a business span, span field, or event, or deciding whether a value belongs in a trace or a log |

## Working rule

Keep each guide narrow. A reusable pattern belongs here when it applies across
multiple backend features and is backed by current code. Product-specific
behaviour belongs in its domain or workflow document; exact generated outputs
belong in reference or generated documentation.

## Related documents

- [[backend|Backend implementation]]
- [[testing|Testing workflow]]
- [[database-migrations|Database migrations]]
