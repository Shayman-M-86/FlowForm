# Admin Results: Session Tree & Bulk Decryption

## The Problem

Viewing results for a survey means answering "which subjects responded, what
did each of their sessions look like, and what did they actually say" — and
every answer value is sitting encrypted in the response DB, addressable only
by locator (see [session-and-response-storage.md](session-and-response-storage.md)
and [encryption-model.md](encryption-model.md)). Naively, decrypting a page of
results would mean one KMS-adjacent unwrap per answer. This doc covers how
`admin_results` avoids that and reconstructs a readable tree from encrypted,
locator-addressed rows.

---

## Three Separate Concerns

The service deliberately separates three jobs that could easily collapse into
one tangled function:

1. **Tree traversal** (`core/session_tree.py`) — group sessions by subject,
   attach answer slots, attach event timelines. Pure core-DB shape-building,
   no crypto.
2. **Bulk decryption** (`core/decryption.py`) — resolve locators and decrypt
   ciphertext. No knowledge of tree shape or export format.
3. **Export formatting** (`core/export.py`) — flatten a tree into rows and
   serialize to JSON or CSV. No knowledge of crypto or DB queries.

Each stage only depends on the previous stage's output type, not its
internals.

---

## Building the Tree

`group_sessions_by_subject()` fetches all sessions for a set of subject IDs
in one query and buckets them by `project_subject_id` (sessions with no
subject are dropped). `build_session_result()` then, per session:

1. Fetches that session's answer slots.
2. Bails early if there are none (nothing to decrypt or format).
3. Builds a question-metadata map from the version's question nodes, needed
   to turn a raw answer back into something labeled.
4. Delegates all locator resolution and decryption to
   `resolve_and_decrypt_answers()`.
5. Optionally attaches an event timeline (best-effort — see Loose Threads).

---

## Bulk Decryption: Avoiding Per-Answer KMS Calls

`resolve_and_decrypt_answers()` is the core of why this doesn't hammer KMS:

1. **Resolve all locators at once.** Given the session's slots, derive every
   answer locator in one pass using the session's `linkage_key_version` (the
   linkage key itself comes from the same cache described in
   [encryption-model.md](encryption-model.md), so re-deriving locators for a
   whole page of results doesn't re-fetch the linkage key per slot).
2. **One bulk DB fetch.** `get_by_locators()` fetches every matching
   `response_answers` row in a single query, keyed by raw locator bytes.
3. **Unwrap the session DEK once.** If decrypted values were requested,
   `load_session_envelope_crypto_context()` resolves the session locator,
   fetches the one `response_envelope` row for the session, and unwraps its
   session DEK exactly once — using the same cache layer as the write path,
   so a previously-unwrapped DEK for an active session doesn't cost a fresh
   unwrap.
4. **Decrypt in a loop, in memory.** With the DEK already in hand, decrypting
   each answer is local AES-GCM — no further network calls.

So the KMS-adjacent cost per session is at most one DEK unwrap (cache hit
avoids even that), not one per answer. The expensive step is amortized across
however many answers that session has.

---

## Where Core DB and Response DB Meet

This flow crosses the DB split the same way the write path does, just in
reverse: core DB supplies session and subject metadata plus answer-slot
identity; response DB supplies ciphertext, reached only via the locator
computed from core-DB identifiers. Nothing in `admin_results` joins the two
databases directly — the locator is the only bridge, computed in-process on
each request rather than stored.

---

## Export

`to_export_rows()` flattens a session tree into one row per answer slot (or
a single metadata-only row if the session has no answers yet).
`format_export_file()` turns that row list into either a JSON array or a CSV
with a fixed column set. Both formats carry the same fields: session
metadata, question key, answer family, whether the value is encrypted vs.
decrypted, and the decrypted value if requested.

---

## Summary

| Stage | Input | Output | Crosses DBs? |
|---|---|---|---|
| Tree traversal | subject IDs | sessions grouped by subject, with slots | Core DB only |
| Locator resolution | answer slot IDs + linkage key version | locator bytes | Core DB only (derivation) |
| Bulk fetch | locator bytes | ciphertext rows | Response DB only |
| Decryption | ciphertext + session DEK | plaintext answer values | Response DB only |
| Export | session tree + decrypted values | JSON/CSV rows | — |

---

## Loose Threads

**Export has a silent 10,000-session cap.** When exporting "all" sessions
without an explicit `session_ids` list, the query is limited to 10,000 rows
with no pagination and no indication to the caller that truncation happened.
A survey with more sessions than that will export an incomplete file with no
error.

**Event-timeline loading swallows all exceptions.** If attaching the event
timeline to a session fails for any reason, it's caught and the timeline is
just left out — silently, from the caller's perspective.

**Answer value can be `None` for reasons other than "no answer."** If the
question-metadata lookup for a slot fails, the resolved answer value comes
back `None` even when the underlying ciphertext decrypted successfully. This
is indistinguishable, at the API response level, from an actually-empty
answer.

**Deletion and read paths disagree on missing-envelope handling.**
`delete_session()` raises if the response envelope is missing;
`build_session_result()` (the read path) just proceeds with an empty
`found` set. Same missing-data condition, different failure behavior
depending on which entry point hit it.
