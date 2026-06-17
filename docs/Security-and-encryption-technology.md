You are using **layered encryption**, not just “encrypt the answer”.

**1. Two-database split**

Core DB stores identity/session metadata: project, survey, link, subject, session status, events.

Response DB stores only encrypted answer data: response envelopes, answer locators, ciphertext, nonces, wrapped DEKs. It should not store user IDs, project IDs, survey IDs, link IDs, plaintext question IDs, plaintext answers, or the core session UUID. 

**2. HMAC locators to connect the databases**

The backend uses a versioned **linkage secret** to derive hidden lookup values:

* `session_locator` links a core session to a response envelope.
* `answer_locator` links a session + question to one logical encrypted answer.

These are created with **HMAC-SHA-256**, so the response DB can be queried without exposing the real session ID or question ID. 

**3. Envelope encryption for each response session**

Each submission session gets its own random **DEK**. That DEK encrypts all answer revisions for that response envelope.

The DEK itself is not stored plaintext. AWS KMS generates it and returns:

* plaintext DEK for immediate backend use;
* wrapped/encrypted DEK for storage in `response_envelopes.wrapped_dek`.

The plaintext DEK only lives briefly in backend memory/cache. 

**4. AES-256-GCM for answer payloads**

Each answer save becomes an encrypted revision using **AES-256-GCM**.

You encrypt every answer type, including ratings, choices, text, dates, emails, phone numbers, and cleared-answer state. Each revision gets a fresh 12-byte nonce, and the DB enforces nonce uniqueness per envelope. 

**5. AAD protects row integrity**

You use **Additional Authenticated Data** with AES-GCM. The AAD includes metadata like crypto version, envelope ID, answer ID, answer locator, revision ID, and revision number. This stops someone from silently swapping encrypted rows around. 

**6. Token hashing, not encryption**

Browser resume tokens and link tokens are not encrypted in the DB. They are random high-entropy tokens, sent raw only to the browser, and stored as hashes server-side. Resume tokens use SHA-256 because they are random tokens, not passwords. 

So the simple version is:

**Core DB knows who/session/status. Response DB only knows anonymous encrypted blobs. HMAC locators connect them. AWS KMS protects the per-session DEK. AES-256-GCM encrypts each answer revision. Tokens are stored as hashes only.**
