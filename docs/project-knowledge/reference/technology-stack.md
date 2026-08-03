---
title: Technology stack
aliases: ["Technology stack", "Tech stack"]
document_type: reference
status: verified
authority: canonical
verified_evidence_digest: sha256:0576a574c37b4dd54c72e0724ce15df77e6008ffd6d143b199814e169efa0051
last_edited: 2026-08-04
tags: [backend, frontend, infrastructure, tooling]
related_code:
  - "../../../backend/pyproject.toml"
  - "../../../frontend/package.json"
  - "../../../infra/deployment/aws/cdk/pyproject.toml"
change_triggers:
  - "../../../.agents/"
  - "../../../.claude/"
  - "../../../.codex/"
  - "../../../.githooks/"
  - "../../../frontend/"
  - "../../../infra/"
  - "../../../scripts/"
  - "../../../tools/"
  - "../../../.github/workflows/"
related_docs:
  - "Reference documentation"
  - "Repository ownership and entry points"
  - "Generated reference documentation"
  - "Deployment architecture"
---

# Technology stack

This is a durable technology-family guide, not a version inventory. Dependency
manifests and generated dependency output are authoritative for exact packages,
constraints, action versions, and image selections.

## Core application

Python and Flask provide the backend API, with Gunicorn owning the production
worker process. Pydantic supplies typed settings and API validation; SQLAlchemy
supplies ORM, session, and query foundations; and Flask-Migrate/Alembic and
checked-in PostgreSQL schemas support schema evolution. The application
generates an OpenAPI 3.1 contract from Flask route metadata and Pydantic models.

PostgreSQL supplies separate core and response-data stores. Auth0 supplies the
external operator-identity boundary, while AWS services support key management,
versioned secrets, email delivery, IAM database authentication, and deployment
concerns. Cryptography and OpenTelemetry libraries support the response-data
and observability boundaries described elsewhere; their presence does not by
itself establish effective deployed policy or telemetry delivery.

## Frontend

The browser workspace uses Node, pnpm, TypeScript, Vite, Astro, React, and
Tailwind. Studio uses TanStack Router for its file-based application route
tree, TanStack Query for server state, Auth0 for browser identity,
React Hook Form and Zod for selected form boundaries, and OpenAPI Fetch plus
its React Query adapter for typed backend access. The Public Site uses Astro's
file and content routing with React islands only where client interactivity is
required.

Shared workspace packages provide builder, generated schema, UI, design-token,
and site-shell capabilities. OpenAPI, RBAC, shared builder schema/constraint,
and Studio route artifacts are generated rather than hand-maintained.

## Infrastructure

Container composition supports development, runtime, and rehearsal contexts.
Caddy and related network services supply edge concerns. AWS deployment uses
CDK and managed cloud services; machine-image and Proxmox tooling support the
other supported deployment paths. Telemetry flows through OpenTelemetry and
the configured logging, metrics, and tracing pipeline.

## Automation and development tooling

FlowForm treats development tooling as part of the engineering system rather
than as a loose collection of convenience commands. Repeated, cross-boundary,
or destructive work is moved behind repository-owned interfaces with explicit
inputs, prerequisites, failure behaviour, and validation evidence. Small,
focused checks support iteration; broader gates are selected by the ownership
boundary before merge or release. Source, tests, configuration, and automation
remain authoritative over prose.

The tooling estate covers workstation and local-runtime orchestration; source
generation and API-contract synchronization; linting, type analysis, security
scanning, tests, builds, and documentation checks; database, container,
machine-image, and deployment operations; and agent guidance, post-edit
feedback, and bounded development or research integrations. These capabilities
provide fast feedback near an edit, prevent checked-in and generated artifacts
from drifting apart, make operational work repeatable, and record which
boundary was actually checked. The presence of a tool is not proof that it ran,
and static validation is not evidence of deployed health.

One of the strongest choices is reuse of the same underlying operations across
developer commands, commit checks, hosted workflows, and release tooling. API
metadata becomes an independently checked contract and downstream artifacts
rather than being manually recopied. Validation is generally separated from
deployment or mutation, live-provider checks are explicit, secrets have defined
delivery boundaries, and higher-risk infrastructure flows favour deliberate
confirmation, dry runs, immutable identifiers, and recorded output. AI support
follows the same model: repository-specific guidance narrows context, shared
hooks provide inexpensive feedback, source-backed integrations expose compact
current evidence, and human review remains the acceptance boundary.

The main improvement pressure is consistency across a large and growing
tooling surface. Discoverability and ownership should keep becoming clearer;
shell automation, developer integrations, frontend interactions, and
less-frequently used infrastructure paths need more uniform automated testing
and static analysis; and conditional hosted or deployment paths need routine
exercise so their orchestration does not drift. Parallel agent configuration
and command documentation also need active synchronization. Consolidation is
valuable where commands duplicate ownership, while local hooks should remain
fast and change-aware enough that their safeguards are practical to keep
enabled.

## Related documents

- [[reference-index|Reference documentation]]
- [[repository-map|Repository ownership and entry points]]
- [[generated-index|Generated reference documentation]]
- [[deployment-index|Deployment architecture]]
