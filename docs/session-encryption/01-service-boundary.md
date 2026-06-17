# Service Boundary

## Purpose

This document defines the boundary of the session response encryption service.

The service is responsible for safely creating, updating, reading, completing, exporting, and deleting encrypted response data. It is not responsible for access authorization.

## Upstream assumptions

By the time this service runs, upstream code has already handled:

- public slug resolution;
- link token resolution;
- survey visibility checks;
- authenticated-link verification;
- subject resolution;
- recognition-token action decisions;
- single-use link policy decisions.

The response encryption service treats those as already-decided inputs.

## Service-owned responsibilities

The service owns:

- creating the response envelope for a core submission session;
- deriving response-side locators from core-side identifiers;
- storing answer payloads only as encrypted revisions;
- loading canonical answers for completion, admin detail, and export;
- blocking public answer hydration while a session is in progress;
- enforcing session lifecycle states for answer mutation;
- ensuring answer writes are authoritative and analytics events are secondary;
- preventing plaintext answer material and key material from leaking into the wrong layer.

## Inputs it trusts structurally, then validates

The service receives a core session context that includes:

- core submission session ID;
- project ID;
- survey ID;
- frozen survey version ID;
- response store ID;
- session status;
- expiry timestamp;
- linkage key version.

The service must validate that the session is active, unexpired, not abandoned, and not completed before accepting respondent edits.

## Respondent-facing outputs

Respondent-facing command outputs are limited to:

- session-start acknowledgement with status, start time, expiry time, and survey version ID;
- answer-save acknowledgement;
- validation errors;
- completion state;

Survey schema delivery belongs to public survey discovery and link-resolution flows. The response encryption service does not add a public current-session read route.

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

API handlers must stay thin. Repositories must touch one database at a time. Services coordinate cross-database work. Crypto helpers expose only narrow operations: deriving locators, creating DEKs, unwrapping DEKs, encrypting answer payloads, and decrypting answer payloads.
