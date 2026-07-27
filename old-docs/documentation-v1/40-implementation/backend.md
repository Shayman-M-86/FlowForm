---
title: Backend implementation
aliases:
  - "Backend implementation"
document_type: implementation
status: draft
authority: canonical
verified_against_commit: ad26b87e9820
tags: [backend]
related_code:
  - "../../backend/wsgi.py"
  - "../../backend/app/core/factory.py"
  - "../../backend/app/api/v1/"
  - "../../backend/app/services/"
  - "../../backend/app/repositories/"
  - "../../backend/app/schema/"
  - "../../backend/tests/"
  - "../../backend/openapi.yaml"
related_docs:
  - "Backend implementation guides"
  - "Repository map"
  - "Component map"
  - "Database migrations"
  - "Testing workflow"
  - "API routes"
  - "Generated files"
---

# Backend implementation

Maps backend concepts to verified repository implementation.

For construction-level guidance, examples, and reusable patterns, use
[[40-implementation/backend/README|Backend implementation guides]]. This page remains the concise
map of the backend rather than becoming a file-by-file handbook.

## Directory ownership

- `backend/app/api/v1/` owns the Flask HTTP boundary. Its account, Studio,
  respondent, and system blueprints are mounted below `/api/v1`.
- `backend/app/services/` and `backend/app/domain/` own use-case coordination
  and domain policy. Public submission and administrative result flows have
  dedicated subpackages because they coordinate encryption and both stores.
- `backend/app/repositories/` owns persistence queries. Core and response
  repositories remain separate, matching the two database-session boundary.
- `backend/app/schema/api/` owns request and response models;
  `backend/app/schema/orm/` owns handwritten SQLAlchemy mappings for the core
  and response schemas.
- `backend/app/core/`, `middleware/`, `aws/`, `crypto/`, `email_service/`, and
  `logging/` provide application assembly and cross-cutting runtime services.

## Entry points

- `backend/wsgi.py` constructs the Flask application through
  `app.create_app()` and is the Gunicorn target `wsgi:app`.
- `backend/app/core/factory.py:create_app` loads settings, initializes
  extensions and both request-scoped database sessions, registers API
  blueprints, rate limiting, error handlers, OpenAPI support, and seed data.
- `backend/app/api/v1/__init__.py` is the route-registration index.
- `backend/scripts/run-tests.sh` is the supported Docker-backed test entry
  point; `export-openapi.sh` and `healthcheck.py` own contract export and
  container-health entry points.

## Important modules

- `app/core/config.py` validates the nested environment model and loads
  mounted secret files before attaching settings to Flask.
- `app/core/extensions.py` assembles authentication, AWS clients, email,
  caching, CORS, and the dual-database manager.
- `app/db/manager.py` creates independent core and response engines;
  `app/db/session.py` opens and closes one session for each store per request.
- `app/middleware/auth/` verifies Auth0 identities, while access services and
  API decorators apply application permissions.
- `app/crypto/`, `services/public_submissions/`, and
  `services/admin_results/` form the response encryption, persistence, and
  authorized decryption boundary.

## Dependency direction

The observed direction is HTTP routes to services/domain policy, then to
repositories and database sessions. API schemas sit at the HTTP boundary and
ORM schemas at the persistence boundary. Cross-cutting extensions are created
centrally and consumed by services or middleware. This layering is a code
convention rather than a mechanically enforced import rule.

Core and response transactions are independent. Cross-store workflows must
commit, compensate, or reconcile explicitly; there is no distributed database
transaction.

## Generated versus handwritten code

Backend Python, API schemas, ORM mappings, and SQL initialization schemas are
handwritten. `backend/openapi.yaml` is generated from registered Python routes
and schema metadata by `app.openapi.export`; it then drives the checked-in
frontend API and schema outputs described in [[generated-files|Generated
files]]. Generated contract files must be refreshed through
`scripts/ci/sync-openapi.sh`, not edited independently.

## Tests and validation

- `backend/tests/unit/` isolates domain, schema, crypto, logging, and service
  behavior.
- `backend/tests/integration/` exercises Flask, Auth0-facing behavior, both
  databases, crypto, models, and environment assembly; `tests/e2e/` holds the
  broader API scenarios.
- `backend/scripts/run-tests.py` fingerprints environment, image, and schema
  inputs to rebuild the Docker test stack only when required.
- `scripts/ci/check-openapi-contracts.sh` checks OpenAPI and frontend generated
  output drift. `check-integrity-rule-constraints.sh` is intended to cross-check
  database constraints and application integrity rules, but its Python helper
  still resolves the removed `infra/postgres/...` schema path and is not a valid
  check at this baseline.

## Known gaps

`Flask-Migrate` is declared as a dependency, but there is no checked-in Alembic
migration repository or initialized Flask-Migrate extension. Database creation
currently belongs to the maintained SQL under `infra/database/init/`, so the
linked migration workflow remains unresolved. Cross-store recovery is also
implemented per use case rather than guaranteed by one transaction boundary.

## Related documents

- [[40-implementation/backend/README|Backend implementation guides]]
- [[repository-map|Repository map]]
- [[component-map|Component map]]
- [[database-migrations|Database migrations]]
- [[testing|Testing workflow]]
- [[api-routes|API routes]]
- [[generated-files|Generated files]]
