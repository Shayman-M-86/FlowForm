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

The raw browser resume token should only be returned or set as a cookie after the required core and response records both exist.

## 2. Current-session loading

A current-session loader should be shared by resume, answer save, question-viewed events, and completion.

It should:

- read the browser resume cookie;
- hash the raw resume token;
- load the core session by token hash;
- load the frozen survey version;
- reject missing, expired, abandoned, invalid, or completed sessions when the command requires editing;
- derive the session locator;
- load the response envelope;
- return a safe service context.

The loader should not expose internal IDs, locators, key material, ciphertext, or nonce values to the browser.

## 3. Answer save

Saving an answer means creating a new encrypted revision.

The response write is authoritative. The core analytics event is secondary.

The conceptual order is:

1. validate and lock the current session when mutation requires it;
2. check whether a revision with the same client mutation ID already exists for this logical answer; if it does, return that revision immediately without proceeding;
3. validate the answer against the frozen survey version;
4. derive the session locator and answer locator;
5. load the response envelope;
6. load the plaintext DEK from the local worker cache, otherwise unwrap it with KMS using `wrapped_dek`;
7. encrypt the answer payload;
8. insert a new immutable revision;
9. update the latest pointer for the logical answer;
10. commit the response transaction;
11. insert the core answer-saved event;
12. commit the core transaction.

If the analytics event fails after the response write succeeds, the answer should still be treated as saved.

## 4. Question-viewed event

Question-viewed events are analytics metadata.

They should validate that the question belongs to the frozen survey version, then write to the core event log. Failure to write this event should not block the respondent from continuing.

## 5. Completion

Completion uses the canonical latest answer set.

The service should:

- load and lock the current session;
- return the existing completed state if already completed;
- load and decrypt latest revisions;
- validate required questions, visible rule paths, answer shapes, and cleared states;
- mark the core session as completed;
- insert a session-completed event;
- reject later respondent edits.

Completion should be idempotent. A repeated completion request for an already completed session should return the stored completion state rather than creating duplicate effects.

## 6. Admin reads and export

Admin list views can mostly use core metadata.

Admin detail and export must go through the authorized decrypt path:

- authorize project and survey access;
- load core session metadata;
- derive session locator;
- load response envelope;
- load latest revisions or history when explicitly requested;
- decrypt through the service;
- map decrypted question IDs to the frozen survey version.

Admin paths should never bypass authorization, locator derivation, or the decrypt service.

## 7. Delete

Deletion should remove encrypted response material before claiming response deletion is complete.

If deletion spans both databases and only one side succeeds, the system should mark the deletion as pending and retry rather than pretending the operation fully completed.
