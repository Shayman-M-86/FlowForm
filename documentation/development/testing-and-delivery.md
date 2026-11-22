# Testing and delivery

**Status: Documentation contract.**

Testing establishes correctness at function, service, API and end-to-end boundaries. Database migrations and permission enforcement require tests against representative persistence and authentication behaviour.

Delivery should identify formatting, linting, type checking, security scanning, image or artifact building, staging validation and production promotion as applicable to the actual pipeline.

This page records the authoritative workflow files, merge requirements, generated artifacts and rollback triggers after they are verified. Deployment approval is distinct from a green test suite.
