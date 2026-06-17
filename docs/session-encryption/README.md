# Session Response Encryption Concepts

This folder explains the target shape of FlowForm's encrypted response system.

It is intentionally narrower than the older session-response-encryption notes. It does not re-document subject resolution, link access, survey visibility, or participant assignment. Those flows are treated as upstream decisions that have already produced a valid submission session context.

## Purpose

FlowForm needs to collect survey answers while reducing what any single database can reveal.

The core database owns application and session metadata. The response database owns encrypted answer material. The backend is the only layer allowed to connect the two, and it does so through versioned cryptographic locators rather than direct database foreign keys.

## Main idea

One respondent run through one frozen survey version creates:

- one core submission session;
- one response envelope;
- many logical answers;
- many immutable encrypted answer revisions.

The response database should not know who the respondent is, which project they belong to, which survey they completed, which link they used, or which plaintext question IDs they answered. It should only store opaque locators, encrypted payloads, nonces, and wrapped key material.

## What is in scope

- Creating a response envelope when a session starts.
- Loading a current session from the browser resume cookie.
- Saving answers as encrypted immutable revisions.
- Tracking the latest canonical answer for each question.
- Completing a session after validating the canonical answer set.
- Reading, exporting, and deleting responses through authorized service paths.
- Managing locators, envelope keys, answer encryption, key versions, and safe logging.

## What is out of scope

- Deciding whether a public slug, general link, private link, or authenticated link is allowed.
- Deciding which subject wins when recognition tokens, login identity, or assigned participants conflict.
- Re-explaining recognition-token lifecycle.
- Re-explaining survey visibility rules.
- Frontend UX details beyond the public contract it must obey.

Those policies are upstream. This service starts after access and subject resolution have produced a core submission session candidate.

## Document map

- `01-service-boundary.md` — where the encryption/session-response service starts and ends.
- `02-storage-and-locators.md` — core/response database split and opaque locator model.
- `03-session-envelope-lifecycle.md` — conceptual lifecycle from session start to completion.
- `04-answer-revisions.md` — answer slots, immutable revisions, clearing, idempotency, and concurrency.
- `05-crypto-key-model.md` — linkage secrets, DEKs, KEKs, AES-GCM, AAD, caching, and rotation.
- `06-failure-and-logging-rules.md` — cross-database ordering, failure handling, observability, and privacy rules.

## Agent rule

When implementing a feature, load only the concept file for that concern, then inspect the current schema/API docs as needed. Do not pull subject-resolution docs into response-encryption work unless the bug is explicitly about subject/access behavior.
