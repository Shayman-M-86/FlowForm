# Implementation Order

Staged rollout plan, version-one decisions, and the final architecture summary.

## 38. Implementation order

Implement the system in stages.

### Stage 1: Database foundations

Complete:

* core submission-session tables;
* project-subject relation;
* core event tables;
* response-envelope tables;
* logical-answer tables;
* immutable revision tables;
* migrations for both databases;
* explicit core and response SQLAlchemy sessions.

### Stage 2: Cryptographic adapters

Implement:

* Secrets Manager linkage-secret provider;
* linkage-secret cache;
* locator service;
* KMS DEK provider;
* DEK cache;
* AAD builder;
* AES-256-GCM answer cipher;
* encryption tests.

### Stage 3: Session creation and resume

Implement:

* access resolution;
* optional project-subject resolution;
* frozen survey-version binding;
* browser resume token generation;
* secure cookie handling;
* response-envelope provisioning;
* session resume;
* current-answer decryption.

### Stage 4: Answer saving and revision history

Implement:

* backend answer validation;
* answer-locator lookup;
* first-save path;
* changed-answer path;
* clear-answer path;
* canonical pointer updates;
* client mutation idempotency;
* concurrency tests.

### Stage 5: Completion and abandonment

Implement:

* final canonical validation;
* completion status transition;
* abandoned-session maintenance task;
* expired-session rejection;
* partial-response retention rules.

### Stage 6: Administrator reads and exports

Implement:

* RBAC checks;
* canonical response reads;
* optional revision-history reads;
* exports;
* privileged-access audit logging.

### Stage 7: Operational hardening

Implement:

* reconciliation tasks;
* pending deletion handling;
* CloudTrail monitoring;
* metrics;
* Sentry sanitisation;
* key-rotation runbooks;
* production IAM policies;
* failure alerts.

---

## 39. Version-one decisions

The initial production implementation should use the following choices.

```text
Backend:
    Python + Flask + SQLAlchemy 2.0

Databases:
    Separate PostgreSQL core and response databases

Response encryption:
    AES-256-GCM
    one random DEK per response envelope
    fresh 12-byte nonce per immutable revision
    stable AAD format
    encrypted JSON payloads

DEK protection:
    AWS KMS GenerateDataKey
    dedicated response-envelope KMS KEK
    wrapped DEK stored with envelope
    plaintext DEK cached briefly in backend memory

Cross-database lookup:
    HMAC-SHA-256 locators
    versioned linkage secret
    linkage secret stored in AWS Secrets Manager
    linkage secret protected by separate KMS key
    linkage secret cached briefly in backend memory

Respondent resume:
    random high-entropy browser token
    raw token in secure HttpOnly cookie
    SHA-256 token hash in core database

Respondent identity:
    optional project_subjects row in the core database
    submission_sessions.project_subject_id points to project_subjects.id
    null project_subject_id means fully anonymous at the core identity layer
    response database stores no project subject identifiers

Answer history:
    stable logical-answer row
    immutable encrypted revisions
    canonical latest-revision pointer
    no separate confirmation pointer

Retry handling:
    browser-generated client_mutation_id
    idempotent save behaviour

Completion:
    latest successfully committed answers become final
    respondent edits rejected after completion

Cross-database coordination:
    service-layer orchestration
    no distributed transaction
    response answer write is authoritative
    analytics are secondary metadata

Security operations:
    narrow IAM permissions
    CloudTrail visibility
    sanitised logs
    no plaintext secret persistence
```

---

## 40. Final architecture summary

A FlowForm survey attempt begins as a core submission session.

That core session receives a random UUID and a hashed browser resume token.

If access resolution identifies a known project participant, the session also
points to `project_subjects.id`; otherwise `project_subject_id` remains null.

The backend loads a versioned linkage secret from Secrets Manager and uses it to derive an opaque session locator.

The session locator identifies an anonymous envelope in the response database.

AWS KMS generates one random session DEK.

The encrypted DEK is stored with the response envelope.

The plaintext DEK exists only temporarily in backend memory and may be cached briefly while the survey remains active.

Each question answer receives an opaque HMAC-derived answer locator.

Each saved value becomes a new immutable encrypted revision.

A fresh nonce is generated for every revision.

The stable logical-answer row points to the latest successfully saved revision.

Earlier encrypted revisions remain preserved.

When the participant completes the survey, the current latest revisions become the final submitted answers.

The core database knows the submission lifecycle.

The response database holds the sensitive encrypted payloads.

Neither database independently contains the complete picture.

The backend joins them only when an authorised workflow requires it.

## Reference notes

[AWS-1] AWS KMS GenerateDataKey returns a plaintext data key and an encrypted copy. AWS states that the plaintext key is used to encrypt data outside KMS and should then be erased from memory, while the encrypted copy is stored with the encrypted data.

[AWS-2] AWS recommends using an encryption context with symmetric KMS operations. The exact context is required again for decryption, and it must not contain sensitive information because it appears in plaintext in CloudTrail logs.

[AWS-3] AWS Secrets Manager encrypts secrets using KMS-backed envelope encryption. AWS also recommends client-side caching, including a Python caching component, to improve speed and reduce API usage.

[AWS-4] AWS KMS supports protected HMAC keys and the GenerateMac operation.

[AWS-5] For symmetric KMS ciphertext blobs, specifying the KMS key during decryption is optional but recommended so the application uses the intended key.

[AWS-6] AWS states that KMS API operations are captured as CloudTrail events.

[AWS-7] AWS KMS direct Encrypt handles plaintext values up to 4,096 bytes. AWS directs applications toward data keys for encrypting application data outside KMS.

[CRYPTO-1] The Python cryptography documentation describes AEAD encryption as providing ciphertext confidentiality and integrity while authenticating associated data. Its AESGCM interface warns that a nonce must never be reused with the same key and returns ciphertext with the authentication tag appended.
