# Session and Response Envelope Lifecycle

## Purpose

This document explains the conceptual lifecycle of encrypted response collection.

## 1. Session start

Session start is not complete until both stores have the required records.

The core side creates a submission session with:

- frozen survey version;
- response store reference;
- browser resume token hash;
- lifecycle timestamps;
- linkage key version.

The response side creates a response envelope with:

- session locator;
- linkage key version;
- wrapped DEK;
- KMS key reference;
- KMS context version;
- crypto version.

The raw browser resume token must only be returned as a cookie after the required core and response records both exist.

## 2. Current-session loading

A current-session loader is shared by answer save, question-viewed events, and completion.

It must:

- read the browser resume cookie;
- hash the raw resume token;
- load the core session by token hash;
- load the frozen survey version;
- reject every forbidden edit state: missing session, expired session, abandoned session, invalid session, and completed session;
- derive the session locator;
- load the response envelope;
- return a safe service context.

The loader must not expose internal IDs, locators, key material, ciphertext, and nonce values to the browser.

## 3. Answer save

Saving an answer means creating a new encrypted revision.

The response write is authoritative. The core analytics event is secondary.

The conceptual order is:

1. validate and lock the current session when mutation requires it;
2. check whether a revision with the same client mutation ID already exists for this logical answer; if it does, return that revision immediately without proceeding;
3. validate the answer against the frozen survey version;
4. derive the session locator and answer locator;
5. load the response envelope;
6. load the plaintext DEK from the local worker cache; on cache miss, unwrap it with KMS using `wrapped_dek`;
7. encrypt the answer payload;
8. insert a new immutable revision;
9. update the latest pointer for the logical answer;
10. commit the response transaction;
11. insert the core answer-saved event;
12. commit the core transaction.

If the analytics event fails after the response write succeeds, the answer must still be treated as saved.

## 4. Question-viewed event

Question-viewed events are analytics metadata.

They must validate that the question belongs to the frozen survey version, then write to the core event log. Failure to write this event must not block the respondent from continuing.

## 5. Completion

Completion uses the canonical latest answer set.

The service must:

- load and lock the current session;
- return the existing completed state if already completed;
- load and decrypt latest revisions;
- validate required questions, visible rule paths, answer shapes, and cleared states;
- mark the core session as completed;
- insert a session-completed event;
- reject later respondent edits.

Completion must be idempotent. A repeated completion request for an already completed session must return the stored completion state rather than creating duplicate effects.

## 6. Admin reads and export

Admin list views can mostly use core metadata.

Admin detail and export must go through the authorized decrypt path:

- authorize project and survey access;
- load core session metadata;
- derive session locator;
- load response envelope;
- load the latest revision set for detail reads;
- load revision history for authorized history reads;
- decrypt through the service;
- map decrypted question IDs to the frozen survey version.

Admin paths must never bypass authorization, locator derivation, and the decrypt service.

## 7. Delete

Deletion must remove encrypted response material before claiming response deletion is complete.

If deletion spans both databases and one side succeeds, the system must mark the deletion as pending and retry rather than pretending the operation fully completed.
