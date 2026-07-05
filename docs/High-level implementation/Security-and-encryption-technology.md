You are using **layered encryption**, not just "encrypt the answer".

**1. Two-database split**

Core DB stores identity/session metadata: project, survey, link, subject, session status, events, and the wrapped survey branch key.

Response DB stores only encrypted answer data: response envelopes, answer locators, ciphertext, nonces, wrapped session DEKs. It does not store user IDs, project IDs, survey IDs, link IDs, plaintext question IDs, plaintext answers, or the core session UUID.

**2. HMAC locators to connect the databases**

The backend uses a versioned **linkage secret** to derive hidden lookup values:

* `session_locator` links a core session to a response envelope.
* `answer_locator` links a session + question to one logical encrypted answer.

These are created with **HMAC-SHA-256**, so the response DB can be queried without exposing the real session ID or question ID.

**3. Three-tier key hierarchy — this is why KMS isn't called per session**

Encryption keys are layered so that a KMS call only happens once per survey, not once per response:

* **Tier 1 — Survey branch key.** Created lazily the first time a survey is published. AWS KMS generates and wraps this key; the wrapped form is stored in Core DB (`survey_encryption_keys.wrapped_survey_branch_key`). The plaintext branch key is unwrapped via one KMS `Decrypt` call and then cached in-process, keyed by `(project_id, survey_id)`. Every session on that survey reuses the cached plaintext branch key — no further KMS calls until the cache is evicted.
* **Tier 2 — Session DEK.** Each submission session gets its own random 32-byte DEK (`os.urandom`), generated locally — not by KMS. It is wrapped locally with AES-256-GCM using the plaintext survey branch key (not KMS directly), and the wrapped form is stored in `response_envelopes.wrapped_session_dek`. Unwrapping a session DEK is a local AES-GCM operation, not a KMS call.
* **Tier 3 — Answer payloads.** The plaintext session DEK encrypts each answer's ciphertext with AES-256-GCM.

So the only place KMS is actually invoked is wrapping/unwrapping the survey branch key — one call per survey (amortized via the in-process cache), not one call per session or per answer.

**4. AES-256-GCM for answer payloads**

Each answer save encrypts (or re-encrypts) the current answer row using **AES-256-GCM**.

Every answer type is encrypted, including ratings, choices, text, dates, emails, phone numbers, and cleared-answer state. Each write gets a fresh 12-byte nonce, and the DB enforces nonce uniqueness per envelope (`uq_response_answers_envelope_id_nonce`).

There is no answer revision history. `response_answers` holds one current row per `answer_locator`; a save overwrites that row in place via `upsert_current()` (`INSERT ... ON CONFLICT (answer_locator) DO UPDATE`). Old ciphertext is not retained.

**5. AAD protects row integrity**

AES-GCM uses **Additional Authenticated Data** bound to database context, not just the plaintext:

* Answer payloads: `crypto_version`, `envelope_id`, `answer_locator`.
* Session DEK wraps: `crypto_version`, `project_id`, `survey_id`, `session_id`, `session_locator`.

This stops a ciphertext row from being silently swapped to a different envelope, answer, or session and still decrypting successfully.

**6. Token hashing, not encryption**

Browser resume tokens and link tokens are not encrypted in the DB. They are random high-entropy tokens (`secrets.token_urlsafe`), sent raw only to the browser, and stored as SHA-256 hashes server-side. Resume tokens use SHA-256 because they are random tokens, not passwords — there is nothing to brute-force offline the way there is with a low-entropy password.

So the simple version is:

**Core DB knows who/session/status, and holds the KMS-wrapped survey branch key. Response DB only knows anonymous encrypted blobs. HMAC locators connect them. AWS KMS protects the per-survey branch key (one KMS call per survey, cached); that branch key locally wraps each session's DEK (no KMS call per session). AES-256-GCM encrypts the current answer row per question, with no revision history. Tokens are stored as hashes only.**
