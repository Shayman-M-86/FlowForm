# Session and Response Envelope Lifecycle

## Purpose

This document explains the conceptual lifecycle of encrypted response collection.

## 1. Session start

Session start is not complete until both the Core DB and Response DB have the required records.

The flow is:

1. Resolve access using `AccessResolver`.

   The respondent may enter through a public slug or a link token.

   This returns a `SubmissionAccessGrant`, which says:

   * which survey/project/version is being accessed;
   * whether the link is valid;
   * what access type is being used;
   * whether a link is assigned;
   * whether authentication is required;
   * whether the link is single-use.

2. Look up the browser recognition token using `SubjectTokenService.lookup`.

   This checks whether this browser is already linked to a known project subject.

   If the token is missing, expired, revoked, or invalid, it returns `None`.

3. Resolve the final subject using `SubjectResolver`.

   This decides which `project_subject_id` the session belongs to.

   It may choose:

   * the assigned link subject;
   * the logged-in user subject;
   * the recognised browser-token subject;
   * a new anonymous subject;
   * no subject, if anonymous subjects are not being created.

   It may also decide whether the recognition token should be issued, rotated, marked used, or kept.

4. Create the Core DB submission session.

   The core side stores:

   * frozen survey version;
   * project subject, if known;
   * link id, if used;
   * browser resume token hash;
   * lifecycle timestamps;
   * linkage key version;
   * session status.

5. Derive the session locator using `LocatorService.for_new_session(session_id)`.

   `LocatorService` uses `LinkageKeyService.get_current()` to get the current linkage key version and secret.

   It returns:

   * `linkage_key_version`;
   * `session_locator`.

6. Generate a plaintext session DEK.

   This DEK is used to encrypt answer payloads for this session.

7. Wrap the DEK using KMS.

   The wrapped DEK is stored in the Response DB.

   The plaintext DEK may be cached by `SessionDEKService` for the active session window.

8. Create the Response DB response envelope.

   The response side stores:

   * session locator;
   * linkage key version;
   * wrapped DEK;
   * KMS key reference;
   * KMS context version;
   * crypto version.

9. Apply the recognition-token action using `SubjectTokenService.apply_token_action`.

   This may issue, rotate, mark used, or keep the browser recognition token.

10. Return browser cookies only after the required Core DB and Response DB records both exist.

The browser may receive:

* the raw resume token cookie;
* the raw recognition token cookie, if one was issued or rotated.

The raw resume token must not be returned if the session and response envelope were not both created successfully.

## 2. Current-session loading

A current-session loader is shared by answer save, completion, and other session-bound operations.

It must:

1. read the browser resume cookie;

2. hash the raw resume token;

3. load the core session by token hash;

4. load the frozen survey version;

5. reject forbidden states:

   * missing session;
   * expired session;
   * abandoned session;
   * invalid session;
   * completed session, unless the operation allows idempotent completion;

6. derive the session locator using `LocatorService.for_existing_session(session_id, linkage_key_version)`;

7. load the response envelope by session locator;

8. return a safe service context.

The safe context may include:

* core session;
* frozen survey version;
* session locator;
* response envelope.

The loader must not expose internal IDs, locators, key material, ciphertext, or nonce values to the browser.

## 3. Answer save

Saving an answer means creating a new encrypted revision.

The response write is authoritative. The core analytics event is secondary.

The flow is:

1. load and lock the current session using the shared current-session loader;

2. check whether a revision with the same client mutation ID already exists for this logical answer;

3. if it exists, return that revision immediately without creating another revision;

4. load the question node from the session’s frozen survey version using the submitted `question_node_id`, then validate the submitted answer against that frozen question definition using the answer validator;

   Validation is performed for a single question at a time.

   This step compares the answer payload to the frozen question schema and constraints only.

   It does not evaluate survey rules, visibility logic, completion state, or cross-question requirements.

5. derive the answer locator using `LocatorService.answer_locator(session_id, question_node_id, linkage_key_version)`;

6. load the plaintext DEK using `SessionDEKService.get_for_session(...)`;

   On cache hit, return the cached DEK.

   On cache miss, unwrap the envelope’s `wrapped_dek` with KMS and cache the plaintext DEK.

7. encrypt the answer payload with AES-GCM using a fresh nonce;

8. insert a new immutable answer revision;

9. update the latest pointer for the logical answer;

10. commit the response transaction;

11. insert the core answer-saved event;

12. commit the core transaction.

If the analytics event fails after the response write succeeds, the answer must still be treated as saved.

Answer save validates the shape of one answer. It does not decide whether the whole submission is complete.

## 4. Question-viewed event

Question-viewed events are analytics metadata.

The flow is:

1. load the current session;
2. load the frozen survey version;
3. validate that the question belongs to the frozen survey version;
4. write the question-viewed event to the core event log.

This path does not need to unwrap the DEK.

Failure to write this event must not block the respondent from continuing.

## 5. Completion

Completion validates access to the current session in the same way as other session-bound operations and then marks the session as completed in the Core DB.

The flow is:

1. load and lock the current session using the shared current-session loader;
2. if the session is already completed, perform no additional work;
3. mark the core session as completed;
4. insert a session-completed event.

Completion must be idempotent. A repeated completion request for an already completed session must not create duplicate effects.

## 6. Admin reads and export

Admin list views can mostly use core metadata.

Admin detail and export must go through the authorized decrypt path.

The flow is:

1. authorize project and survey access;
2. load core session metadata;
3. load the frozen survey version;
4. derive the session locator using `LocatorService.for_existing_session(session_id, linkage_key_version)`;
5. load the response envelope;
6. load the latest revision set for detail reads;
7. load revision history for authorized history reads;
8. load the plaintext DEK using `SessionDEKService.get_for_session(...)`;
9. decrypt through the service;
10. map decrypted answers back to the frozen survey version.

Admin paths must never bypass authorization, locator derivation, or the decrypt service.

## 7. Delete

Deletion must remove encrypted response material before claiming response deletion is complete.

The flow is:

1. authorize deletion;
2. load the core session;
3. derive the session locator using the stored linkage key version;
4. load the response envelope;
5. delete encrypted response answers, answer history, and response envelope;
6. mark or delete the core session record;
7. clear any cached plaintext DEK using `SessionDEKService.clear_for_session(session_id)`.

If deletion spans both databases and one side succeeds, the system must mark the deletion as pending and retry rather than pretending the operation fully completed.
