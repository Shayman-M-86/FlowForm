# Answer Storage and Revisions

## Purpose

This document explains how answers are represented once a session has a response envelope.

## Model

The response side has three conceptual layers.

`response_envelopes` holds one encrypted response container for one submission session.

`response_answers` holds one logical answer slot per envelope and question locator.

`response_answer_revisions` holds immutable encrypted revisions for that logical answer.

## Canonical answer

The canonical answer is the latest revision pointed to by the logical answer row.

This avoids scanning the full history every time the current answer state is needed.

## Immutable history

Answer revisions are append-only.

When a respondent changes an answer, the old ciphertext stays in history and a new encrypted revision is added. The logical answer row moves its latest pointer forward.

## Clearing an answer

Clearing an answer is not deletion.

A clear operation creates a new encrypted revision with a cleared state and a null answer value. Earlier revisions remain unchanged.

## First save

On first save for a question:

- derive the answer locator;
- create the logical answer row if it does not exist;
- create revision 1;
- set the latest pointer to revision 1.

Simultaneous first saves should be handled by the unique logical answer constraint and retried or resolved safely.

## Changed answer

On a changed answer:

- find the logical answer row by envelope and answer locator;
- lock it;
- read the current latest revision number;
- insert the next revision number;
- move the latest pointer forward.

Revision numbers should be sequential within one logical answer.

## Idempotency

Each answer mutation should carry a client mutation ID.

The same mutation ID for the same logical answer should return the existing saved revision rather than creating a duplicate revision.

This protects against network retries, browser retries, and lost HTTP responses.

## Concurrency

The logical answer row is the concurrency boundary.

Lock the logical answer row when calculating the next revision number. Use the unique answer locator constraint for simultaneous first saves. Treat retries with the same client mutation ID as idempotent, not conflicting.

## Validation rule

The backend must validate answers against the frozen survey version before saving.

Frontend validation is useful for UX but not trusted for persistence.
