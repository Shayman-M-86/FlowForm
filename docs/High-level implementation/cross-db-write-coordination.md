# Cross-DB Write Coordination

## The Problem

Core DB and response DB are two separate PostgreSQL databases with no shared
foreign keys (see [session-and-response-storage.md](session-and-response-storage.md)).
A single logical operation — starting a session, for example — needs a row in
each. Postgres cannot give us a single ACID transaction spanning both. Something
has to define what "committed" means when the two writes can't be atomic
together.

---

## What This Is Not

The docs use the word "saga" loosely, and it's worth being precise: this is
**not** a saga pattern with compensating transactions defined per step. There
is no orchestrator that knows how to undo an arbitrary completed step. What
exists is narrower — a specific two-phase commit order with a best-effort
cleanup attempt, backed by an asynchronous reconciliation sweep for whatever
the best-effort cleanup misses.

`commit_with_err_handle` (`db/error_handling/error_registry.py`) is the
low-level primitive: it commits, and on `DBAPIError` rolls back and translates
the error into a typed exception. It has no knowledge of any other database —
it cannot roll back a sibling commit in a different DB. All cross-DB ordering
and cleanup logic lives in the calling service, not in this helper.

---

## The Pattern: Response First, Core Second

`session_starter.py` is the canonical example. The order is deliberate:

1. **Response DB write first.** Create the `response_envelope` row (session
   locator, wrapped session DEK, crypto version) and commit it.
2. **Core DB write second.** Create the `submission_session` row, consume the
   link if single-use, and commit.

If step 1 fails, nothing in core DB has been touched yet — a clean abort.

If step 2 fails *after* step 1 already committed, the response envelope is now
orphaned (a response DB row with no matching core session). The service
attempts a **best-effort compensating delete**: remove the orphaned envelope
by locator and commit that deletion.

This ordering is not arbitrary — it fails toward the cheaper-to-clean-up side.
An orphaned response envelope is inert (no session ever references it,
nothing reads it). An orphaned core session, if it existed, would be visible
in listings and participant history — a worse failure mode. So the design
accepts "orphan a response row" as the failure case it's willing to leave
behind if cleanup itself fails.

---

## When Cleanup Itself Fails

If the compensating delete in step 2's failure path also fails (response DB
unreachable, etc.), the code does **not** retry or suppress the original
error. It logs at CRITICAL and re-raises the original `SessionStartError`.
The orphaned envelope is left in place, undiscovered, until reconciliation
finds it.

---

## Reconciliation: The Backstop

`public_submissions/core/reconciliation.py` provides
`reconcile_orphaned_sessions()`, an asynchronous sweep — not triggered inline
by any request — that:

1. Scans in-progress `submission_session` rows in core DB.
2. For each, derives the session locator and checks whether a matching
   `response_envelope` exists.
3. If missing, marks the core session `abandoned`.

Note the asymmetry: reconciliation looks for core sessions with **no**
response envelope (the case where step 2 never completed, or the row was
manually removed), not for response envelopes with no core session. The
best-effort delete in `session_starter.py` is assumed to handle the latter;
reconciliation is the backstop for the former, and for any envelope-cleanup
failure that logged CRITICAL and moved on.

Reconciliation is not real-time. Between a partial failure and the next
reconciliation run, an orphaned or abandoned-but-unmarked session can exist.
This is an accepted tradeoff, not an oversight — synchronous cross-DB rollback
would require either distributed transactions (not available across two
independent Postgres instances) or blocking the request on a second network
round-trip's confirmation.

---

## Summary

| Phase | DB | On failure |
|---|---|---|
| 1. Create response envelope | Response | Rollback both DBs, raise — nothing else has happened yet |
| 2. Create core session | Core | Attempt to delete the now-orphaned envelope (best-effort) |
| 2a. Cleanup delete fails | Response | Log CRITICAL, re-raise original error, orphan persists |
| Backstop | Core (reads response) | Async sweep marks orphaned-looking core sessions `abandoned` |

---

## Loose Threads

**Reconciliation only looks one direction.** It finds core sessions without a
response envelope. It does not appear to independently sweep for response
envelopes without a matching core session — those rely entirely on the
inline best-effort delete succeeding. If that delete silently fails in a way
that doesn't hit the CRITICAL log path, the orphan has no second chance to be
found.

**No retry/backoff on the compensating delete.** It's a single attempt. A
transient response DB blip during cleanup is treated the same as a permanent
failure.

**Other cross-DB call sites** (`answer_save.py`, `admin_results/core/decryption.py`,
`participants.py`) don't all follow the same two-phase-with-cleanup shape —
some are read-only across both DBs, which sidesteps the coordination problem
entirely. This doc describes the write-coordination pattern specifically; not
every cross-DB service needs it.
