# Backend architecture

**Status: Current implementation is Flask; Litestar-based modular monolith is a target design.**

The existing API is implemented in Python with Flask. A redesign is being considered around Litestar and a feature-based modular monolith. This page defines the target organization without presenting it as deployed.

The proposed codebase groups application operations into **features**, supported by **API infrastructure**, **workers**, **capabilities**, **repositories**, **models**, **errors** and external integrations. Features own the operations exposed by the API; capabilities own reusable functionality available to different execution environments.

A dedicated domain layer is not required by default. Abstractions are introduced only where they clarify ownership or enable reuse.

See [Features and capabilities](features-and-capabilities.md), [API and authorization](api-and-authorization.md), and [Repositories and transactions](repositories-and-transactions.md).
