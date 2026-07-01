# Architecture

Cross-cutting architecture decisions that shape both the backend and frontend.

* [Two-database privacy model](two-database-model.md) - `core` vs `response` PostgreSQL databases, linked pseudonymously
* [Survey versioning model](survey-versioning.md) - draft/published/archived immutable versions
* [OpenAPI-driven API contract](openapi-contract.md) - runtime-generated OpenAPI 3.1 spec as source of truth
* [Authentication and authorization](auth.md) - Auth0 JWTs plus project/survey RBAC
* [CI pipeline](ci-pipeline.md) - GitHub Actions security, test, and build stages
