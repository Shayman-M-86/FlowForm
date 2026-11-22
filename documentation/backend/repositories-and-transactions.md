# Repositories and transactions

**Status: Target conventions.**

Repositories implement explicit queries and persistence operations and return well-defined shapes. They do not silently issue database requests through attribute access. Data transfer objects or typed models may represent query results without requiring full ORM entities.

Transaction scope is established by the executing workflow, commonly an API request service or worker operation. Repositories operate with the provided session or transaction context; they do not independently commit unrelated business operations.

Database constraints remain authoritative. Application error mapping may use stable PostgreSQL error codes and named constraints instead of parsing localized error strings.

The final SQLAlchemy, raw SQL and session-dependency choices must be validated against the Litestar implementation.
