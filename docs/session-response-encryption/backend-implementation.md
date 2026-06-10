# Backend Implementation

Service structure, interfaces, API surface, implementation-driven schema notes, and local development guidance.

## 28. Backend service structure

Keep cryptography, database access and submission workflows separate.

Recommended package structure:

```text
app/
├── crypto/
│   ├── answer_cipher.py
│   ├── aad.py
│   ├── locator.py
│   ├── dek_cache.py
│   ├── linkage_secret_provider.py
│   └── kms_dek_provider.py
│
├── repositories/
│   ├── core/
│   │   ├── submission_sessions.py
│   │   ├── submission_events.py
│   │   ├── survey_versions.py
│   │   └── project_subjects.py
│   │
│   └── response/
│       ├── response_envelopes.py
│       ├── response_answers.py
│       └── response_answer_revisions.py
│
├── services/
│   └── submissions/
│       ├── access_resolver.py
│       ├── session_starter.py
│       ├── session_resumer.py
│       ├── answer_saver.py
│       ├── session_completer.py
│       ├── response_reader.py
│       ├── response_exporter.py
│       ├── response_deleter.py
│       └── reconciliation.py
│
├── domain/
│   └── submissions/
│       ├── models.py
│       ├── payloads.py
│       └── errors.py
│
└── api/
    └── routes/
        ├── public_submissions.py
        └── responses.py
```

### 28.1 Repository rule

A repository should normally access only one database.

Examples:

```text
CoreSubmissionSessionRepository
ResponseEnvelopeRepository
ResponseAnswerRepository
ResponseRevisionRepository
```

Do not place cross-database workflows inside repositories.

### 28.2 Service rule

Submission services orchestrate workflows across repositories.

Example:

```text
AnswerSaver
```

may use:

```text
CoreSubmissionSessionRepository
CoreSubmissionEventRepository
ResponseEnvelopeRepository
ResponseAnswerRepository
ResponseRevisionRepository
LocatorService
LinkageSecretProvider
DekProvider
AnswerCipher
CompiledSchemaValidator
```

### 28.3 Crypto boundary

Keep raw cryptographic operations out of API routes and repositories.

API route:

```text
parse request
call service
serialize response
```

Crypto service:

```text
derive locators
obtain DEKs
construct AAD
encrypt payload
decrypt payload
```

---

## 29. Suggested service interfaces

### 29.1 Linkage-secret provider

```python
class LinkageSecretProvider:
    def get_secret(self, version: int) -> bytes:
        ...
```

Responsibilities:

* retrieve the correct versioned secret;
* cache it briefly;
* reject unknown versions;
* never log secret values.

### 29.2 Locator service

```python
class SubmissionLocatorService:
    def derive_session_locator(
        self,
        *,
        linkage_secret: bytes,
        session_id: UUID,
    ) -> bytes:
        ...

    def derive_answer_locator(
        self,
        *,
        linkage_secret: bytes,
        session_id: UUID,
        question_node_id: UUID,
    ) -> bytes:
        ...
```

### 29.3 DEK provider

```python
class ResponseDekProvider:
    def generate_for_envelope(
        self,
        *,
        envelope_id: UUID,
    ) -> GeneratedDek:
        ...

    def get_plaintext_dek(
        self,
        *,
        envelope: ResponseEnvelope,
    ) -> bytes:
        ...
```

Return shape:

```python
@dataclass(frozen=True)
class GeneratedDek:
    plaintext_dek: bytes
    wrapped_dek: bytes
    kms_key_arn: str
    kms_context_version: int
```

### 29.4 Answer cipher

```python
class AnswerCipher:
    def encrypt_revision(
        self,
        *,
        plaintext_dek: bytes,
        payload: AnswerPayload,
        context: AnswerEncryptionContext,
    ) -> EncryptedRevision:
        ...

    def decrypt_revision(
        self,
        *,
        plaintext_dek: bytes,
        revision: StoredRevision,
        context: AnswerEncryptionContext,
    ) -> AnswerPayload:
        ...
```

### 29.5 Answer saver

```python
class AnswerSaver:
    def save_answer(
        self,
        *,
        raw_resume_token: str,
        question_node_id: UUID,
        answer_input: object,
        client_mutation_id: UUID,
    ) -> SavedAnswerResult:
        ...
```

---

## 30. Suggested API surface

Exact route names can follow the existing FlowForm API conventions.

A reasonable shape is:

```text
POST   /public/submission-sessions
GET    /public/submission-sessions/current
PUT    /public/submission-sessions/current/answers/{question_node_id}
POST   /public/submission-sessions/current/events/question-viewed
POST   /public/submission-sessions/current/complete
```

Administrator routes:

```text
GET    /projects/{project_id}/surveys/{survey_id}/responses
GET    /projects/{project_id}/surveys/{survey_id}/responses/{session_id}
GET    /projects/{project_id}/surveys/{survey_id}/responses/{session_id}/history
POST   /projects/{project_id}/surveys/{survey_id}/responses/export
DELETE /projects/{project_id}/surveys/{survey_id}/responses/{session_id}
```

---

## 35. Implementation-driven schema notes

The schema file remains the source of truth.

The following small additions are recommended because they support the runtime logic described above.

### 35.1 Response envelope additions

Add:

```text
kms_context_version SMALLINT NOT NULL
```

### 35.2 Revision additions

Add:

```text
client_mutation_id UUID NOT NULL
```

Enforce:

```text
UNIQUE (answer_id, client_mutation_id)
```

### 35.3 Optional core event deduplication

If analytics events must be strictly idempotent, add an optional deduplication identifier to core submission events.

This can be introduced later if duplicate analytics events become a real issue.

---

## 36. Local development

### 36.1 Provider abstraction

Do not couple submission logic directly to live AWS clients.

Implement interfaces:

```text
LinkageSecretProvider
ResponseDekProvider
```

Production adapters use:

```text
AWS Secrets Manager
AWS KMS
```

Development and unit-test adapters may use local test secrets and deterministic fake responses.

### 36.2 Development-only keys

Local development values must never match production values.

Store local values through the existing development secret-file approach.

Do not commit them to Git.

### 36.3 Integration testing

Use two PostgreSQL test databases.

Continue using explicit paired fixtures:

```text
core_db_session
response_db_session
```

Tests must prove that cross-database services behave correctly without relying on cross-database foreign keys.

---
