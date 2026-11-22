# Data boundaries

**Status: Current separation of core and response data; further identity-isolation ideas are proposed.**

FlowForm separates management and identifying records from survey answer storage. The core data store holds account, project and participant-management context. The response store holds answer data associated with published survey versions.

The boundary limits unnecessary access to identity-linked responses. It is not, by itself, a guarantee of anonymity: linkage services, metadata, timing, backups and authorized re-identification paths must be included in the threat model.

More restrictive service separation and cryptographic cooperation between services are proposals and require a dedicated reviewed design before being described as operational.

See [Encryption](encryption.md) and [Identity and permissions](identity-and-permissions.md).
