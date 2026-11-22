# System overview

**Status: Current at the product-boundary level; deployment details must be verified per environment.**

FlowForm comprises client-facing applications, an application API, independent data stores and platform infrastructure.

The Studio interface creates and manages project and survey resources. The participant interface loads published survey versions and collects answers. The API mediates identity, permissions, publishing, participant access, persistence and response review.

The core data store owns account, project and survey-management records. Response data is stored separately to reduce unnecessary coupling between identifying records and answer values. Authorized application logic resolves the relationship when required.

Infrastructure provides ingress, service execution, data storage and deployment mechanisms. The exact deployed services are documented in [Environments](../infrastructure/environments.md).

See [Component boundaries](component-boundaries.md), [Data boundaries](../data-security/data-boundaries.md), and [Request lifecycles](request-lifecycles.md).
