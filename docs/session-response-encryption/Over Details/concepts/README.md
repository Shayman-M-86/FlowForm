# Session Response Encryption Concepts

This folder explains the target service behavior for session response
encryption.

It starts after FlowForm has already resolved access, resolved the subject
where one exists, and created a core `submission_sessions` row. Those
subject/access decisions are important prerequisites, but they are not the
focus here. This folder is about the response-encryption service itself:
how it creates anonymous response storage, encrypts answer revisions, and
lets authorized backend workflows read or remove those answers later.

## What We Want

FlowForm should be able to collect survey answers without letting the response
database learn who the respondent is or which core records identify them.

The target behavior is:

1. The core service creates a submission session for a frozen survey version.
2. The response-encryption service creates one anonymous response envelope for
   that session.
3. Each answer save becomes an encrypted, append-only revision in the response
   database.
4. Core lifecycle events and response payloads stay separate.
5. Admin read, export, and deletion workflows can decrypt or remove responses
   only after core-side authorization has already succeeded.

The browser should not receive raw encryption keys, response database IDs, or
an endpoint for reading arbitrary in-progress encrypted answers.

## Boundary

The response-encryption service owns:

- deriving opaque response-side locators from core IDs;
- creating `response_envelopes`;
- generating, wrapping, unwrapping, and caching per-session DEKs;
- encrypting answer payloads;
- appending answer revisions;
- selecting the latest canonical encrypted revision for a question;
- decrypting answers for authorized backend workflows.

It does not own:

- survey-link access rules;
- authenticated-link participant checks;
- subject resolution;
- recognition-token policy;
- public route authorization;
- Studio admin authorization;
- survey-answer validation rules.

Those decisions happen before this service is called. The service receives the
minimum stable identifiers and canonical answer payloads it needs to do its
job.

## Docs In This Folder

- [Response encryption service](response-encryption-service.md) - the target
  service contract, data boundaries, and lifecycle.

## Related References

- [Architecture](../architecture.md) - broader core/response storage split.
- [Data model](../data-model.md) - exact tables and constraints.
- [API surface](../api-surface.md) - current route status and placeholders.
- [Cryptography plan](../cryptography-plan.md) - detailed crypto design.
- [Remaining work](../remaining-work-fixed.md) - implementation phases.
