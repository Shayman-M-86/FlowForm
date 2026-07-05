# Validation Ladder — Full Reference

Prefer focused validation after each pass:

```bash
bash backend/scripts/run-tests.sh --ai -k "<focused selector>"
```

Climb the ladder as risk rises:

1. **Unit tests** — crypto helpers, locator derivation, envelope construction.
   No DB fixtures. Inject bytes, dicts, fakes, or monkeypatches directly.
2. **Repository tests** — response DB repositories with `response_db_session`.
   Verify constraint handling, get-or-create races, and DB routing.
3. **Service tests** — session start, answer save, completion logic with
   `db_sessions` (cross-DB). Test business decisions in isolation.
4. **Integration tests** — full session lifecycle: start → save answers →
   load → complete. Verify cross-DB consistency and encryption round-trips.
5. **Route/API tests** — endpoint contracts, cookie behavior, error responses.
   Verify no plaintext leaks in response payloads.
6. **Broader backend validation** — run after changes to shared domain,
   auth, transaction boundaries, or repository behavior:
   `bash backend/scripts/run-tests.sh --ai`

Useful selectors for this workflow:

* `crypto` — AES-GCM helpers, DEK cache, KMS wiring
* `response_repo` — response DB repositories
* `session_start` or `submission_session` — session lifecycle
* `answer_save or session_loader` — answer collection and loading
* `completion or admin_decrypt or deletion` — completion and admin paths
* `crypto_smoke` — AWS wiring smoke tests

Skipped validation is not green. Record what was skipped and why in the
pass report under "Failures or skipped validation".
