---
title: Responses and encryption
aliases: ["Responses and encryption"]
document_type: domain
status: draft
authority: canonical
verified_against_commit: null
tags: [security]
related_code:
  - "../../../backend/app/crypto/"
  - "../../../backend/app/schema/orm/response/"
  - "../../../backend/app/services/public_submissions/core/actions/"
  - "../../../backend/app/services/admin_results/"
  - "../../../backend/app/db/manager.py"
  - "../../../infra/database/init/schema/flowform_response_db_schema_v4.sql"
related_docs:
  - "Data knowledge"
  - "Security model"
  - "Trust boundaries"
---

# Responses and encryption

FlowForm keeps identity-bearing and survey metadata in a core store while the
response store contains encrypted answer material addressed through derived
opaque locators. This is data minimisation at rest, not a protection boundary
against a compromised backend process: the backend opens both stores and has
access to the linkage and decryption material needed for authorized results.

## Data and key boundaries

The response-side ORM and SQL schema model response envelopes and answers rather
than users, projects, surveys, subjects, or core foreign keys. A response
envelope carries an opaque session locator, a linkage-key version, and wrapped
session-key material. Answer rows carry an opaque answer locator, ciphertext,
nonce, and response metadata. Core records provide the identity and lifecycle
context used to derive those locators.

The crypto package implements a layered design: a survey key is wrapped with
AWS KMS, a session key is wrapped under that survey key, and the session key
encrypts answer payloads using AES-GCM with associated data. Linkage locators
are derived with a separately versioned linkage secret. Runtime key and locator
caches reduce remote reads and unwraps, which means plaintext material can be
present in backend worker memory while in use.

```text
KMS key
   |
   v
wrapped survey key
   |
   v
wrapped session key
   |
   +--> encrypt answer + nonce + associated data
   |              |
   |              v
   |         ciphertext in response store
   |
linkage secret --> opaque session / answer locators
```

## Lifecycle

When a submission session begins, application services derive a session locator,
create response-envelope state, and coordinate that state with the core session.
Saving an answer derives an answer locator and stores an encrypted current value.
Authorized result paths start from core authorization and metadata, resolve the
response-side material, and decrypt it in the backend. Individual-session
deletion is coordinated across the two stores rather than protected by one
database transaction.

```text
Core authorization + metadata
              |
       derive opaque locator
              |
              v
      Response envelope/answer
              |
       unwrap key + decrypt
              |
              v
     authorized backend result
```

## Limits and review needs

The two stores are independently modelled but cross-store work is
application-coordinated, so partial failures need compensation and reconciliation
behaviour. The implementation also leaves operational questions outside this
page: deployment credential separation, KMS/IAM policy, backups, rotation,
cache eviction, and handling of plaintext after an authorized read require
separate evidence.

## Related documents

- [[data-index|Data knowledge]]
- [[security-model|Security model]]
- [[trust-boundaries|Trust boundaries]]
