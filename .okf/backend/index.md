# Backend

Flask API layers, from HTTP boundary down to persistence. See the
[two-database privacy model](/architecture/two-database-model.md) for how
cross-database work is constrained to the service layer.

* [backend/app/api/v1/](api-v1.md) - HTTP boundary, thin route handlers
* [backend/app/services/](services.md) - use-case orchestration layer
* [backend/app/repositories/](repositories.md) - persistence helpers
* [backend/app/domain/](domain.md) - durable business rules
* [backend/app/schema/](schema.md) - Pydantic contracts and ORM mappings
* [backend/tests/](tests.md) - unit, integration, and e2e test layout
