# Service Boundary

## Purpose

This document defines the boundary of the session response encryption service.

The service is responsible for safely creating, updating, reading, completing, exporting, and deleting encrypted response data. It is not responsible for deciding whether the respondent was allowed to access the survey.

## Upstream assumptions

By the time this service runs, upstream code has already handled:

- public slug or link token resolution;
- survey visibility checks;
- authenticated-link verification;
- subject resolution;
- recognition-token action decisions;
- single-use link policy decisions.

The response encryption service should treat those as already-decided inputs.

## Service-owned responsibilities

The service owns:

- creating the response envelope for a core submission session;
- deriving response-side locators from core-side identifiers;
- storing answer payloads only as encrypted revisions;
- loading canonical answers for resume, completion, admin detail, and export;
- enforcing session lifecycle states for answer mutation;
- ensuring answer writes are authoritative and analytics events are secondary;
- ensuring no plaintext answer material or key material leaks into the wrong layer.

## Inputs it can trust structurally, but still validates

The service may receive a core session context that includes:

- core submission session ID;
- project ID;
- survey ID;
- frozen survey version ID;
- response store ID;
- session status;
- expiry timestamp;
- linkage key version.

The service should still validate that the session is active, unexpired, not abandoned, and not completed before accepting respondent edits.

## Outputs it may return to clients

Respondent-facing outputs may include:

- session status;
- expiry information;
- frozen survey schema when appropriate;
- save acknowledgements;
- validation errors;
- completion state;
- safe canonical answers when a current-session route exists.

Respondent-facing outputs must not include:

- core session ID;
- response envelope ID;
- session locator;
- answer locator;
- linkage key version details beyond what the server needs;
- wrapped DEK;
- plaintext DEK;
- KMS key ARN;
- nonce;
- ciphertext;
- plaintext answers belonging to another session.

## Main boundary rule

API handlers should stay thin. Repositories should touch one database at a time. Services should coordinate cross-database work. Crypto helpers should only expose narrow operations such as deriving locators, creating or unwrapping DEKs, encrypting answer payloads, and decrypting answer payloads.
