# API and authorization

**Status: Current authentication exists; the request-coordination design below is proposed.**

The API establishes identity, validates incoming requests, authorizes operations and maps application results to HTTP responses. Authentication and authorization are separate: a valid identity does not itself imply access to a resource.

The proposed Litestar API may use guards and dependencies for common authentication and permission resolution. Short-lived resource-scoped authorization tokens could reduce repeated permission lookups; token scope, signature, expiry and revocation trade-offs require a separate design decision.

Speculative asynchronous authorization is a separate proposal: safe preparatory service work may run while a permission lookup is pending, but protected side effects cannot cross the authorization barrier. Cancellation, transaction isolation and failure behaviour must be defined before adoption.

API reference content should come from a generated [OpenAPI definition](../reference/api-reference.md), not hand-maintained endpoint descriptions.
