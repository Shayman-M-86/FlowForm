## LinkageKeyService

### Purpose

`LinkageKeyService` manages the linkage secrets used to derive session locators and answer locators.

### Location

This service will probably sit inside, or be used by, a higher-level `LocatorService`.

### Methods

`get_current()` is used when creating a new session and response envelope. It returns the current linkage key version and secret.

`get_by_version(version)` is used for existing sessions and envelopes. It returns the exact secret for the stored `linkage_key_version`.

### Secret Loading

The service should call AWS Secrets Manager only when the requested key is not already cached in memory.

### Rotation Behaviour

New sessions use the current linkage key. Existing sessions keep using the key version they were created with, so their session and answer locators remain stable after rotation.

---

## LocatorService

### Purpose

`LocatorService` derives opaque locators used to connect Core DB records to Response DB records without exposing real IDs.

### Location

This service should use `LinkageKeyService` to get the correct linkage secret, then derive locators from stable Core DB IDs.

### Methods

`for_new_session(session_id)` is used when creating a new session and response envelope. It uses the current linkage key and returns the `linkage_key_version` and `session_locator`.

`for_existing_session(session_id, linkage_key_version)` is used when finding an existing response envelope. It uses the stored linkage key version and returns the same stable `session_locator`.

`answer_locator(session_id, question_node_id, linkage_key_version)` is used when saving, loading, or deleting one answer. It returns the stable `answer_locator` for that session/question pair.

`answer_locators(session_id, question_node_ids, linkage_key_version)` is used for admin detail/export paths. It returns a map of `question_node_id -> answer_locator`.

### Boundaries

`LocatorService` should not fetch envelopes, fetch answers, unwrap DEKs, call KMS, or decrypt data. It only derives locators.

### Rotation Behaviour

New sessions use the current linkage key. Existing sessions and answers always use the stored `linkage_key_version`, so their locators remain stable after rotation.

---

## SessionDEKService

### Purpose

`SessionDEKService` manages plaintext session DEKs after they have been unwrapped from AWS KMS. It is used by answer write/read services when they need the AES key for encrypting or decrypting answers.

### Location

This service should sit below answer read/write services and above the low-level KMS client. It should not know about survey logic or answer validation.

### Inputs Needed

To unwrap a DEK, the service needs:

* `session_id`
* `wrapped_dek`
* `kms_key_arn`
* optional KMS encryption context
* cache expiry time, usually based on the session expiry

The `session_id` is used as the cache key. The `wrapped_dek` is sent to AWS KMS. The `kms_key_arn` is useful for validation/logging and making sure the expected key is being used.

### Methods

`get_for_session(session_id, wrapped_dek, kms_key_arn, expires_at)` returns the plaintext DEK for a session. If the DEK is already cached and not expired, it returns the cached key. Otherwise, it calls AWS KMS `Decrypt`, caches the plaintext DEK, and returns it.

`clear_for_session(session_id)` removes one session DEK from memory. This should be called when a session is completed, abandoned, deleted, or expired.

`clear_expired()` removes expired cached DEKs from memory.

### Caching Behaviour

The plaintext DEK should be cached in memory per API worker/process. The cache should last only for the active session window, or shorter. Each worker has its own cache.

### Nonce Note

The DEK service does not manage answer nonces. Nonces belong to individual AES-GCM answer encryptions and are stored with each encrypted answer row. KMS-wrapped DEKs do not need you to separately store a nonce; KMS returns and accepts the encrypted key blob as a whole.
