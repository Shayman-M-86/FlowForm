# Component boundaries

**Status: Current product boundaries; backend module layout is under redesign.**

The **frontend** owns user interaction, local presentation state and experience-specific navigation. It does not independently decide authorization.

The **API** owns request-level validation, identity handling, permission enforcement and coordination of application operations.

**Feature services** implement operations belonging to a functional area and may be coupled to the API execution model.

**Capabilities** supply reusable functions shared by features or execution environments without depending on HTTP request objects.

**Repositories** own explicit persistence operations. Schema and migration definitions establish the database contract.

**Workers**, where present, own independent background execution and reuse appropriate capabilities.

**Infrastructure** owns provisioning, networking, secrets delivery and runtime operations. It does not define product business rules.

See the [Backend modernization proposal](../decisions/backend-modernization.md) for target module boundaries.
