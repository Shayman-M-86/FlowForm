# Features and capabilities

**Status: Target.**

A **feature** represents a functional area of the backend such as projects, surveys, publication or participation. It owns its relevant routes, request and response schemas, feature services and feature-specific errors. Feature services may use API context where useful.

A **capability** owns reusable application functionality without depending on request routing or worker orchestration. Features and workers can call capabilities directly. Examples may include encryption, access-context construction or file processing when justified by actual reuse.

The **API** owns route registration, shared request dependencies, guards and request execution coordination. Workers own their own entry points and execution policies.

Repositories provide explicit persistence operations consumed by features and capabilities. Shared data structures and errors are defined only when they genuinely cross feature boundaries.
