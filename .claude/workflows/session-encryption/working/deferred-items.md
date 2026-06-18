# Deferred Items

Last updated: 2026-06-18

This note gathers known deferred or future-work items found from the current
session-encryption workflow files, live backend code, and prior FlowForm memory
notes. It is a routing aid, not a replacement for the pass reports.

## Session-Encryption Workflow

1. **Canonical answer payload contract**
   FlowForm currently has a session-answer transport envelope, but not a
   canonical domain answer model. `SaveSubmissionSessionAnswerRequest` accepts
   `answer_family` plus `answer_value: dict[str, Any]`, while the encrypted
   plaintext payload currently stores only `answer_state` and `answer_value`.
   There is no settled per-family answer shape for choice, field, matching, or
   rating answers.
   Deferred because: answer save and completion cannot perform reliable domain
   validation until the project decides what submitted answers look like for
   each supported question family and how those shapes are stored/decrypted.
   To complete: define canonical answer payload schemas per question family,
   decide whether `answer_family` belongs in the encrypted plaintext payload,
   and make the public save request, encrypted payload parser/builder, admin
   decrypt responses, exports, scoring, rules, and completion validation all use
   the same answer contract.
    Further context:
   - `backend/app/schema/api/requests/submission_sessions/`
   - `backend/app/crypto/payload.py`
   - `backend/app/services/public_submissions/core/answer_save.py`
   - `backend/app/services/public_submissions/core/admin_decrypt.py`
   - `backend/app/schema/api/requests/content/questions_schemas.py`
   - `backend/app/schema/api/requests/content/rule_schemas.py`

2. **Completion validation engine**
   Completion currently checks a stale/ad hoc top-level
   `question_schema.required` flag. The active question API schemas do not
   define that field; `required` currently appears as a rule effect/state
   concept and in rule condition requirements. Visibility paths, answer shapes,
   conditional display, required-state evaluation, and richer cleared-state
   semantics still need a domain validation engine.
   Deferred because: no backend engine currently interprets the survey's
   visibility/display/required rules, and the canonical answer payload contract
   is not settled yet.
   To complete: after the canonical answer payload contract is defined,
   implement a shared survey-answer validation module and call it from
   `CompletionService._validate_completion()` after decrypting latest answers.
   The new engine should replace the `question_schema.required` shortcut with
   validation against the frozen survey version, evaluated rule state, and the
   canonical submitted answer shapes.
    Further context:
   - `backend/app/services/public_submissions/core/completion.py`
   - `.claude/workflows/session-encryption/working/pass-reports/08-completion-admin-and-deletion.md`
   - `.claude/workflows/session-encryption/working/targets/08-completion-admin-and-deletion/spec.md`
   - `docs/session-encryption/03-session-envelope-lifecycle.md`

3. **Save-answer shape validation**
   Answer save verifies that the question node belongs to the frozen survey
   version, but it does not validate that the submitted answer value matches the
   question's family/schema or a canonical answer payload model. This belongs
   with the same domain validation module as completion validation, but it must
   wait for the answer payload contract decision above.
   Deferred because: Pass 06 only needed encrypted save mechanics and question
   membership; full shape validation needs both a broader schema interpreter
   and settled per-family answer payload schemas.
   To complete: after canonical answer payload schemas exist, hook
   `AnswerSaveService.save_answer()` into the same shared validator used by
   completion before plaintext payload construction/encryption.
    Further context:
   - `backend/app/services/public_submissions/core/answer_save.py`
   - `.claude/workflows/session-encryption/working/pass-reports/06-answer-save-and-session-loader.md`
   - `backend/app/schema/api/requests/submission_sessions/`
   - `backend/app/schema/api/requests/content/questions_schemas.py`

4. **Durable pending deletion**
   Response-first deletion raises `DeletionPendingError` if response deletion
   commits but core deletion fails. No durable pending marker is written yet
   because `submission_sessions.session_status` does not currently include a
   deletion state.
   Deferred because: recording the state durably needs a schema decision, and
   the current status CHECK allows only `in_progress`, `completed`, and
   `abandoned`.
   To complete: add a deletion-pending representation through a migration
   (status value or side table), then have `delete_session_responses()` persist
   it and expose a retry path for the pending core cleanup.
    Further context:
   - `backend/app/services/public_submissions/core/deletion.py`
   - `infra/postgres/init/schema/flowform_core_db_schema_v4.sql`
   - `.claude/workflows/session-encryption/working/pass-reports/08-completion-admin-and-deletion.md`
   - `docs/session-encryption/06-failure-and-logging-rules.md`

5. **Shared DEK unwrap helper refactor**
   Completion and answer-save both carry similar `_get_or_unwrap_dek` logic.
   The duplication is acceptable for the pass, but a shared helper would reduce
   drift in KMS context handling and DEK cache behavior.
   Deferred because: it is a cleanup/refactor, not a blocker for pass behavior,
   and the pass was focused on proving completion/decrypt/delete paths.
   To complete: extract a small internal helper for cached DEK unwrap and switch
   answer save, completion, and any future decrypt/write services to call it.
    Further context:
   - `backend/app/services/public_submissions/core/completion.py`
   - `backend/app/services/public_submissions/core/answer_save.py`
   - `backend/app/crypto/dek_cache.py`
   - `backend/app/crypto/kms.py`

5. **Public answer route still placeholder**
   The public answer endpoint still returns a response-shaped placeholder rather
   than loading the session and delegating to the encrypted answer-save service.
   The API-facing session management method is also still a placeholder.
   Deferred because: encrypted answer-save was built and tested at the service
   layer before replacing the existing public API stub.
   To complete: make `save_submission_session_answer()` read the browser session
   cookie, call `SessionManagementService.save_answer()`, load via
   `load_current_session()`, delegate to `AnswerSaveService.save_answer()`, and
   return the real revision metadata.
    Further context:
   - `backend/app/api/v1/respondent/submission_sessions.py`
   - `backend/app/services/public_submissions/api/session_management.py`
   - `backend/app/services/public_submissions/core/answer_save.py`
   - `backend/app/schema/api/requests/submission_sessions/`

6. **Public event route still placeholder**
   The public event endpoint parses the request and returns `204`, but it does
   not persist the core-side analytics event yet. Event write failures should
   remain secondary to the respondent flow when this is wired.
   Deferred because: event persistence was less critical than encrypted answer
   correctness and completion state changes during the current pass sequence.
   To complete: route `record_submission_session_event()` through
   `SessionManagementService.record_event()`, load the current session, validate
   the question when present, insert `submission_events`, and swallow/log
   secondary event-write failures.
    Further context:
   - `backend/app/api/v1/respondent/submission_sessions.py`
   - `backend/app/services/public_submissions/api/session_management.py`
   - `backend/app/repositories/core/submission_events.py`
   - `backend/app/services/public_submissions/core/answer_save.py`

7. **Admin survey-response API still contract stubs**
   Admin list/detail/history/export/delete routes authorize at the route layer,
   but still return placeholder data or no-op success. They need real service
   wiring that uses core metadata, locator derivation, and decrypt/delete paths.
   Deferred because: Pass 08 created service-layer decrypt/delete primitives,
   while the admin response API was still a contract stub from an earlier phase.
   To complete: add an admin response service that loads authorized core
   sessions for the requested project/survey, calls `decrypt_session_detail()`,
   `decrypt_session_history()`, or `delete_session_responses()`, and maps the
   service results into the existing API response models.
    Further context:
   - `backend/app/api/v1/studio/surveys/responses.py`
   - `backend/app/services/public_submissions/core/admin_decrypt.py`
   - `backend/app/services/public_submissions/core/deletion.py`
   - `backend/app/services/results.py`

8. **Session-start reconciliation repair**
   Pass 09 is intended to repair committed core sessions that have no matching
   response envelope by marking them `abandoned`. This keeps pre-core-commit
   rollback failures distinct from committed-but-unusable sessions.
   Deferred because: it is a distinct repair workflow from normal session start,
   and it needed the completion/admin/deletion pass to settle first.
   To complete: implement `core/reconciliation.py` to scan eligible
   `in_progress` core sessions, derive locators, check the response envelope
   repo, call `submission_sessions.mark_abandoned()` for missing envelopes, and
   add the Pass 09 integration tests.
    Further context:
   - `.claude/workflows/session-encryption/working/targets/09-session-start-reconciliation-repair/spec.md`
   - `docs/session-encryption/06-failure-and-logging-rules.md`
   - `backend/app/services/public_submissions/core/session_loader.py`
   - `backend/app/repositories/core/submission_sessions.py`

9. **Reconciliation scheduler or worker**
   Pass 09 only scopes the service-level repair function and tests. A scheduler,
   CLI, or background worker for running reconciliation repeatedly remains a
   separate operational design task.
   Deferred because: the workflow first needs a safe, tested reconciliation
   function before deciding how operators or automation should run it.
   To complete: after Pass 09 lands, hook the reconciliation service into an
   operator CLI, scheduled worker, admin job, or runbook-controlled command with
   safe logging and counts-only output.
    Further context:
   - `.claude/workflows/session-encryption/working/targets/09-session-start-reconciliation-repair/spec.md`
   - `backend/app/services/public_submissions/core/session_starter.py`
   - `docs/session-encryption/06-failure-and-logging-rules.md`
   - `backend/app/repositories/response/response_envelope_repo.py`

10. **Real AWS/KMS validation**
    Integration tests patch KMS and Secrets Manager calls, so they verify local
    call contracts but not real cloud behavior. Real validation requires
    operator-controlled AWS infrastructure and credentials.
    Deferred because: real AWS validation is environment-dependent and should
    not run in ordinary integration tests or local CI without provisioned
    secrets/KMS keys.
    To complete: create an operator-run smoke test or runbook that uses real
    configured AWS credentials, starts a session, saves/decrypts an answer, and
    verifies wrap/unwrap/linkage-secret behavior without logging key material.
   Further context:
   - `.claude/workflows/session-encryption/working/pass-reports/07-integration-tests-session-and-answers.md`
   - `backend/app/crypto/kms.py`
   - `backend/app/crypto/secrets.py`
   - `backend/tests/integration/response/test_session_start_encryption.py`

11. **Operator DB inspection and sign-off**
    The workflow still calls for human inspection/sign-off of the encrypted
    persistence behavior. Automated tests cover the main paths, but operator
    review is still a separate completion gate.
    Deferred because: this is a human assurance step, not something the agent can
    fully prove with automated tests.
    To complete: have the operator inspect core/response DB rows after the test
    scenarios, confirm no plaintext/key material or forbidden identifiers are
    stored in the wrong database, then record sign-off in the Pass 10 report.
   Further context:
   - `.claude/workflows/session-encryption/working/pass-reports/07-integration-tests-session-and-answers.md`
   - `.claude/workflows/session-encryption/working/targets/10-security-review-and-e2e/spec.md`
   - `docs/session-encryption/02-storage-and-locators.md`
   - `docs/session-encryption/06-failure-and-logging-rules.md`

12. **True concurrency tests**
    Duplicate/update tests currently cover sequential behavior. True concurrent
    first-save races need a multi-threaded or multi-process test harness with
    separate DB sessions.
    Deferred because: the current integration harness exercises deterministic
    sequential flows, and true race testing needs separate connections running
    in parallel.
    To complete: add a concurrency test harness that runs simultaneous first
    saves for the same answer locator from separate DB sessions and asserts one
    logical answer row, ordered revisions, and correct mutation-id handling.
   Further context:
   - `.claude/workflows/session-encryption/working/pass-reports/07-integration-tests-session-and-answers.md`
   - `backend/tests/integration/response/test_answer_save_encryption.py`
   - `backend/app/repositories/response/response_answer_repo.py`
   - `backend/app/repositories/response/response_answer_revision_repo.py`

13. **Security review and final E2E pass**
    Pass 10 remains the final validation gate: security review, full submission
    session E2E tests, finding disposition, and operator sign-off readiness.
    Deferred because: it depends on Pass 09 and the remaining service/API wiring
    being stable enough to review end to end.
    To complete: run the Pass 10 security review scope, run the submission
    session E2E suite, disposition every finding as accept/fix/defer, fix any
    high-severity issues, and write the Pass 10 report.
   Further context:
   - `.claude/workflows/session-encryption/working/targets/10-security-review-and-e2e/spec.md`
   - `backend/app/services/public_submissions/`
   - `backend/app/crypto/`
   - `backend/app/repositories/response/`
   - `backend/app/services/results.py`

14. **Production KMS client optimization**
    KMS and Secrets Manager clients are currently created per call. For
    production throughput, shared or session-scoped clients may be needed after
    correctness and security are settled.
    Deferred because: it is an optimization and lifecycle-management concern,
    not required for correctness of the current encrypted response flow.
    To complete: introduce a safe client factory/session layer that reuses AWS
    clients per process/config while preserving test patchability and credential
    isolation.
   Further context:
   - `.claude/workflows/session-encryption/working/pass-reports/03-aws-wiring-and-crypto-smoke-test.md`
   - `backend/app/crypto/kms.py`
   - `backend/app/crypto/secrets.py`
   - `backend/app/core/config.py`

15. **Crypto/KMS version rotation support**
    Crypto and KMS context versions are currently hardcoded in the service
    implementation. Future rotation support may need these values to come from
    config or persisted version metadata.
    Deferred because: key/version rotation policy has not been designed yet, and
    hardcoded v1 constants are enough for the initial implementation.
    To complete: define rotation semantics, persist/read the relevant crypto and
    linkage/KMS context versions, and hook session start, answer save,
    completion, and admin decrypt into version-aware helpers.
   Further context:
   - `.claude/workflows/session-encryption/working/pass-reports/04-session-start.md`
   - `backend/app/services/public_submissions/core/session_starter.py`
   - `backend/app/services/public_submissions/core/completion.py`
   - `backend/app/services/public_submissions/core/admin_decrypt.py`
   - `docs/session-encryption/05-crypto-key-model.md`

## Older FlowForm Follow-Ups From Memory

16. **General-access session-start subject policy**
    The general-access path still needs an explicit product/domain decision:
    remain anonymous or create a project subject at session start. Do not hide
    this behind a default while participant verification work is stabilizing.
    Deferred because: the correct behavior changes respondent identity semantics
    and should be chosen explicitly, not inferred inside the session starter.
    To complete: decide the general-access subject policy, then update
    `SessionStarter`, `access_resolver`, and `subject_resolver` so the chosen
    behavior is applied consistently for public/general links.
   Further context:
   - `backend/app/services/public_submissions/core/session_starter.py`
   - `backend/app/services/public_submissions/core/access_resolver.py`
   - `backend/app/services/public_submissions/core/subject_resolver.py`
   - `docs/session-response-encryption/Over Details/flows.md`
   - `docs/session-response-encryption/Over Details/data-model.md`

17. **Interrupted e2e fixture cleanup**
    A prior diagnostic noted a likely `_ADMIN_SUB` versus `_MEMBER_SUB` mismatch
    in backend e2e fixtures. The suggested next step was a narrow fixture/import
    cleanup followed by a quick import or lint check.
    Deferred because: that earlier turn was interrupted before a fix landed, and
    it was not part of the session-encryption pass scope.
    To complete: inspect the e2e fixture constants/imports, correct the stale
    `_ADMIN_SUB`/`_MEMBER_SUB` usage if still present, then run a targeted e2e
    import or link-lifecycle test check.
   Further context:
   - `backend/tests/e2e/conftest.py`
   - `backend/tests/e2e/test_survey_link_lifecycle.py`
   - `backend/tests/e2e/test_submission_session_start.py`

18. **Frontend query and builder verification**
    Older frontend follow-ups include direct coverage for query policy,
    persistence, cooldown/cache ownership, and builder import validation around
    duplicate IDs, sort keys, rule direction, and payload limits.
    Deferred because: these were product/frontend hardening follow-ups from a
    separate refactor, not blockers for the backend session-encryption workflow.
    To complete: add targeted Studio query-runtime tests and builder import
    validation tests, then revisit route-consolidation UX, AGENTS drift, and
    bundle-size/code-splitting warnings.
   Further context:
   - `frontend/apps/studio-app/src/lib/query/queryPolicy.ts`
   - `frontend/packages/builder/src/components/Utils/ai-import/surveyNodeImport.ts`
   - `frontend/apps/studio-app/src/lib/query/queryPersistence.ts`
   - `frontend/apps/studio-app/src/lib/query/queryCooldown.ts`
   - `frontend/apps/studio-app/src/lib/query/queryCacheOwner.ts`
   - `frontend/apps/studio-app/AGENTS.md`
