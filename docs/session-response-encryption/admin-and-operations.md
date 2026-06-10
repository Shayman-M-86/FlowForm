# Admin And Operations

Administrator viewing, exports, deletion, cross-database consistency, IAM/KMS configuration, rotation, privacy logging, and failure scenarios.

## 24. Flow: administrator response viewing

### 24.1 Authorisation

Administrator response access is a privileged operation.

Require the appropriate project or survey permission before loading encrypted answers.

Auth0 authenticates the application user.

FlowForm RBAC authorises the action.

### 24.2 Read flow

1. Load the core submission session.
2. Confirm the administrator may view the response.
3. Read `linkage_key_version`.
4. Load the matching linkage secret.
5. Derive `session_locator`.
6. Load the response envelope.
7. Load the wrapped DEK.
8. Check the DEK cache.
9. Call KMS `Decrypt` on cache miss.
10. Load canonical revisions or full history as requested.
11. Rebuild AAD.
12. Decrypt answer payloads.
13. Validate decrypted question IDs and locators.
14. Return the authorised response view.

### 24.3 Default response view

The normal administrator response screen should load:

```text
canonical latest revisions only
```

Do not load historical revisions unless the user explicitly opens the answer-history view.

### 24.4 Audit logging

Record privileged response reads in an application audit trail.

Store:

```text
authorised user ID
project ID
survey ID
submission-session ID
action type
timestamp
success or failure
```

Do not store plaintext answers in the audit log.

---

## 25. Flow: exporting responses

Exports follow the same retrieval path as administrator viewing.

### 25.1 Export process

1. Authorise the project-level export permission.
2. Load the selected core submission sessions.
3. Derive session locators.
4. Fetch response envelopes.
5. Unwrap and cache DEKs as needed.
6. Load canonical latest revisions.
7. Decrypt payloads.
8. Validate payloads.
9. Map question-node IDs to the frozen survey-version schema.
10. Build the export file.
11. Deliver the export securely.
12. Record an audit event.

### 25.2 Historical exports

The default export should contain the canonical final answers.

A separate explicit audit export may include answer-revision history if the product needs it.

---

## 26. Flow: deleting a response

Deletion must be coordinated by the backend.

### 26.1 Delete the response envelope first

Before deleting the core session:

1. Load the core session.
2. Read the linkage-key version.
3. Derive `session_locator`.
4. Find the response envelope.
5. Delete the response envelope.
6. Allow local response-database cascades to remove logical answers and revisions.
7. Delete or anonymise the core session according to policy.

Delete the response envelope before deleting the core session.

If the core session is deleted first, the application may lose the easiest way to derive the response locator.

### 26.2 Failure handling

If the response database is temporarily unavailable:

* keep the core session;
* mark deletion as pending;
* retry later;
* do not claim that deletion has completed.

---

## 27. Cross-database consistency

### 27.1 No distributed transaction

The core database and response database use separate SQLAlchemy sessions and separate PostgreSQL transactions.

Do not attempt to make them appear to be one normal transaction.

Use service-layer coordination.

### 27.2 Authoritative source for answers

For answer saves:

```text
The response-database transaction is authoritative.
```

If the encrypted revision committed successfully, the answer is saved.

Core analytics are secondary metadata.

### 27.3 Recommended answer-save coordination

A practical save flow is:

```text
1. Lock and validate the core session.
2. Update core last_activity_at.
3. Save the encrypted response revision.
4. Commit the response transaction.
5. Insert the core answer_saved analytics event.
6. Commit the core transaction.
7. Return success.
```

A rare failure can occur after step 4 but before step 6.

In that case:

* the answer is preserved;
* a browser retry is safe because of `client_mutation_id`;
* core analytics may require repair;
* the respondent should not lose the answer.

### 27.4 Reconciliation process

Add a scheduled reconciliation task.

It should detect:

* core sessions without response envelopes;
* stale session-initialisation failures;
* pending deletions;
* inconsistent linkage-key versions;
* missing response envelopes during administrator retrieval;
* analytics repair items where practical.

Because opaque locators cannot be reversed, reconciliation should usually iterate from core sessions to derived response locators.

### 27.5 Optional future outbox

If exact analytics delivery becomes important, add a durable outbox pattern.

Do not add a distributed-transaction system unless there is a demonstrated need.

---

## 31. IAM and KMS configuration

### 31.1 Use separate KMS keys

Use separate customer-managed KMS keys for separate purposes.

Recommended keys:

```text
flowform-response-envelope-kek
flowform-linkage-secret-kek
```

The first protects wrapped response DEKs.

The second protects the versioned linkage secret stored in Secrets Manager.

Do not use one key for every application purpose.

### 31.2 Runtime permissions

The backend runtime role needs narrowly scoped permissions.

For response-envelope DEKs:

```text
kms:GenerateDataKey
kms:Decrypt
```

restricted to:

```text
flowform-response-envelope-kek
```

For linkage-secret retrieval:

```text
secretsmanager:GetSecretValue
secretsmanager:DescribeSecret
```

restricted to:

```text
flowform/prod/submission-linkage/*
```

The relevant Secrets Manager and KMS policies must permit access to the linkage-secret KMS key.

### 31.3 No frontend AWS permissions

The browser must never call KMS or Secrets Manager.

Only the backend runtime role receives AWS permissions.

### 31.4 Store immutable KMS key ARNs

Store the immutable response-envelope KMS key ARN with each envelope.

Do not rely only on an alias.

Aliases are useful for deployment configuration, but the stored envelope record should identify the actual intended KMS key.

### 31.5 CloudTrail

KMS API operations are recorded in CloudTrail. [AWS-6]

Use this for:

* security monitoring;
* incident investigation;
* unexpected decryption detection;
* key-policy review;
* audit visibility.

---

## 32. Key rotation

Different key types rotate differently.

### 32.1 Response KEK rotation

The response-envelope KEK wraps per-session DEKs.

For new envelopes:

```text
Use the currently active response KEK ARN.
```

For existing envelopes:

```text
Keep the original kms_key_arn.
Continue decrypting wrapped DEKs with the original intended key.
```

Existing ciphertext does not need to be rewritten immediately.

A future maintenance process may rewrap old DEKs under a newer KEK.

### 32.2 Linkage-secret rotation

The linkage secret affects deterministic locators.

Do not replace it without versioning.

Rotation process:

1. Generate a new random linkage secret.
2. Store it as a new Secrets Manager secret version or versioned secret name.
3. Increment the active linkage version.
4. Use the new version for newly created sessions.
5. Retain old versions for old sessions.
6. Continue reading each session using its stored `linkage_key_version`.

Example:

```text
session A → linkage version 1
session B → linkage version 2
```

The backend loads the correct secret for each session.

### 32.3 Crypto-format rotation

Use:

```text
response_envelopes.crypto_version
```

to identify the local encryption format.

A future version may change:

* algorithm;
* payload format;
* AAD layout;
* nonce rules;
* serializer.

Decrypt each envelope according to its stored crypto version.

---

## 33. Logging and privacy rules

### 33.1 Never log sensitive values

Do not log:

* plaintext answers;
* decrypted payloads;
* browser resume tokens;
* link tokens;
* linkage secrets;
* plaintext DEKs;
* KMS plaintext responses;
* complete ciphertext values;
* complete nonces;
* authentication cookies.

### 33.2 Safe structured logging

Safe internal logs may include:

```text
request ID
internal session UUID
envelope UUID
survey version UUID
question-node UUID where appropriate
revision UUID
revision number
status
error category
duration
```

Be careful when logging question-node IDs from conditional surveys, because the path itself may carry meaning.

### 33.3 Sentry and tracing

Sanitise request bodies before sending data to Sentry or tracing tools.

For answer-save endpoints:

```text
capture metadata
exclude answer values
exclude cookies
exclude tokens
```

### 33.4 Metrics

Safe aggregate metrics include:

```text
session starts
session completions
session abandonments
save latency
KMS call count
KMS failure count
DEK cache hit rate
Secrets Manager cache hit rate
response database errors
core database errors
revision count distribution
```

---

## 34. Failure scenarios

### 34.1 KMS unavailable during session start

The backend cannot create the wrapped DEK.

Result:

```text
Do not create an exposed respondent session.
Return a safe temporary error.
Clean up any partial core row.
```

### 34.2 KMS unavailable during an active session save

If the DEK is already in memory cache:

```text
The save may continue.
```

If the DEK is not cached:

```text
Fail safely.
Do not save plaintext.
Return a retryable temporary error.
```

### 34.3 Secrets Manager unavailable

If the required linkage-secret version is already cached:

```text
The request may continue.
```

If it is not cached:

```text
Fail safely.
Do not guess.
Do not generate a different locator.
```

### 34.4 Core database unavailable

Do not allow new sessions to start.

For answer saves, session validation cannot be trusted without the core database.

Fail safely and ask the frontend to retry.

### 34.5 Response database unavailable

Do not claim that an answer was saved.

Return a retryable error.

The browser should retry with the same:

```text
client_mutation_id
```

### 34.6 HTTP response lost after successful save

The browser retries.

The backend detects the existing `client_mutation_id`.

Return the existing revision as success.

Do not create a duplicate revision.

### 34.7 Analytics insert failure

The encrypted answer remains authoritative.

Log the failure.

Repair asynchronously where practical.

Do not tell the respondent that a committed answer was lost.

### 34.8 Invalid ciphertext or authentication failure

Treat this as a serious integrity failure.

Do not return partial plaintext.

Record a security-grade internal error.

Include identifiers needed for investigation, but never log the DEK or decrypted content.

---
