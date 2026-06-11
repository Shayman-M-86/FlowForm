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
│   │   ├── project_subjects.py
│   │   ├── project_subject_identities.py
│   │   ├── project_subject_tokens.py
│   │   ├── subject_ip_observations.py
│   │   └── survey_links.py
│   │
│   └── response/
│       ├── response_envelopes.py
│       ├── response_answers.py
│       └── response_answer_revisions.py
│
├── services/
│   └── submissions/
│       ├── access_resolver.py
│       ├── project_subject_resolver.py
│       ├── subject_recognition_tokens.py
│       ├── subject_identities.py
│       ├── subject_ip_observations.py
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
CoreProjectSubjectRepository
CoreProjectSubjectIdentityRepository
CoreProjectSubjectTokenRepository
CoreSubjectIpObservationRepository
CoreSurveyLinkRepository
ResponseEnvelopeRepository
ResponseAnswerRepository
ResponseRevisionRepository
```

Do not place cross-database workflows inside repositories.

### 28.2 Service rule

Submission services orchestrate workflows across repositories.

`SurveyAccessResolver` resolves the survey and link requirements.
`ProjectSubjectResolver` resolves or creates the optional stable subject.
`SessionStarter` creates the core session and provisions the anonymous response
envelope after access and subject resolution have completed.

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

### 28.4 Project subject boundary

Use `ProjectSubject` / `project_subjects` as the forward respondent identity
relation for the new session system.

The access resolver or a dedicated project-subject service may create or load a
project subject. Identity lookups live around the subject relation through
`project_subject_identities`, `project_subject_tokens`, and assigned survey
links.

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

### 29.6 Project subject resolver

```python
class ProjectSubjectResolver:
    def resolve_for_access(
        self,
        *,
        project_id: int,
        access: SubmissionSessionAccess,
        authenticated_user_id: int | None,
    ) -> UUID | None:
        ...
```

Responsibilities:

* return `project_subjects.id` when the access path identifies a known project
  subject;
* create the project subject when the product rule says the access path should
  materialize one;
* return `None` for fully anonymous sessions;
* resolve authenticated users through `project_subject_identities`;
* resolve subject-recognition tokens through `project_subject_tokens`;
* resolve assigned links through `survey_links.assigned_subject_id`.

---

## 30. Suggested API surface

> The full respondent-facing surface — including request/response shapes,
> status codes, and the frontend call sequences — is specified in
> [api-structure.md](api-structure.md). This section is the summary; that
> document is authoritative for the public routes.

Exact route names follow the existing FlowForm API conventions.

Respondent discovery and access resolution (these reuse pre-existing public
routes; only the verb on link-resolve changes):

```text
GET    /public/surveys
GET    /public/surveys/{public_slug}
POST   /public/links/resolve
```

> **Decision: link-resolve is `POST`, not `GET`.** The existing route is
> `GET /public/links/resolve?token=...`. It moves to `POST` with the token in
> the JSON body so the token never enters query strings, browser history, or
> logs — consistent with the never-log rules in
> [admin-and-operations.md §33.1](admin-and-operations.md). This is a behavior
> change to the existing route, not a new endpoint.

Respondent session lifecycle:

```text
POST   /public/submission-sessions
GET    /public/submission-sessions/current
PUT    /public/submission-sessions/current/answers/{question_node_id}
POST   /public/submission-sessions/current/events/question-viewed
POST   /public/submission-sessions/current/complete
```

> **Decision: sessions are addressed as `current`, never `{session_id}`.** The
> session is identified server-side from the `HttpOnly` resume cookie (hashed
> to `browser_session_token_hash`); the UUID never appears in the URL. The
> `session_id` that the locator service ([§29.2](#292-locator-service))
> consumes is loaded from that row, not taken from the path.

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
