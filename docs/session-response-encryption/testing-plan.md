# Testing Plan

Focused test coverage for locators, encryption, sessions, revisions, idempotency, completion, rotation, and failure cases.

## 37. Test plan

### 37.1 Locator tests

Verify:

* same session ID and same secret produce the same session locator;
* different sessions produce different locators;
* different linkage versions produce different locators;
* session and answer purpose labels cannot collide;
* different question IDs produce different answer locators;
* decrypted question IDs recompute to the stored answer locator.

### 37.2 Encryption tests

Verify:

* encryption followed by decryption restores the payload;
* each save generates a fresh nonce;
* ciphertext changes cause decryption failure;
* nonce changes cause decryption failure;
* AAD changes cause decryption failure;
* wrong DEK causes decryption failure;
* cleared answers decrypt correctly;
* the database rejects nonce reuse within one envelope.

### 37.3 Session-start tests

Verify:

* valid public access starts a session;
* valid link access starts a session;
* expired link access fails;
* inactive link access fails;
* the session binds to one survey version;
* a response envelope is created;
* only a token hash reaches the core database;
* the raw browser token is returned only after both stores succeed;
* an envelope-creation failure does not expose a broken session.

### 37.4 Answer-revision tests

Verify:

* first save creates one logical answer and one revision;
* changed answer inserts revision two;
* the first ciphertext remains unchanged;
* latest pointer moves forward;
* clear-answer state inserts another revision;
* history remains available;
* canonical retrieval returns only the latest revision;
* history retrieval returns all revisions in order.

### 37.5 Idempotency tests

Verify:

* retrying one mutation ID does not create another revision;
* retrying after a simulated lost HTTP response returns success;
* simultaneous first saves produce one logical answer;
* simultaneous changes produce unique sequential revisions.

### 37.6 Completion tests

Verify:

* completion validates canonical answers;
* incomplete required answers prevent completion;
* completion freezes respondent edits;
* repeated completion requests are safe;
* an answer save and completion request cannot race incorrectly.

### 37.7 Rotation tests

Verify:

* old linkage-key versions remain readable;
* new sessions use the active linkage version;
* old wrapped DEKs decrypt with their stored KMS key ARN;
* new envelopes use the active response KEK;
* crypto-version dispatch works.

### 37.8 Failure tests

Verify:

* KMS failure returns a safe error;
* Secrets Manager failure returns a safe error on cache miss;
* cached linkage secrets survive a short Secrets Manager outage;
* cached DEKs survive a short KMS outage;
* response-database failure does not claim save success;
* analytics failure does not delete a committed answer;
* pending deletion retries safely.

---
