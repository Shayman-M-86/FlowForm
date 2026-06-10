# Response Database Schema

Response database tables for anonymous encrypted envelopes, logical answers, and answer revisions.

```sql
-- RESPONSE DATABASE SCHEMA
-- Stores anonymous encrypted survey answers separately from the core database.


CREATE TABLE response_envelopes (
    id                      UUID PRIMARY KEY,

    -- Hidden cross-database lookup. Derived from the core submission_sessions.id
    -- using an external linkage secret.
    session_locator         BYTEA NOT NULL UNIQUE
                            CHECK (octet_length(session_locator) = 32),

    -- Identifies the external linkage-secret version used to derive the
    -- session locator and answer locators.
    linkage_key_version     SMALLINT NOT NULL
                            CHECK (linkage_key_version > 0),

    -- Encrypted copy of the session-specific Data Encryption Key.
    -- One DEK protects all revisions belonging to this envelope.
    wrapped_dek             BYTEA NOT NULL,

    -- Immutable ARN of the KMS-managed Key Encryption Key used to wrap the DEK.
    kms_key_arn             TEXT NOT NULL,

    -- Identifies the local authenticated-encryption format and algorithm.
    crypto_version          SMALLINT NOT NULL
                            CHECK (crypto_version > 0)
);


CREATE TABLE response_answers (
    -- Stable local ID for one logical question answer.
    id                      UUID PRIMARY KEY,

    -- Groups this logical answer under one anonymous response envelope.
    envelope_id             UUID NOT NULL
                            REFERENCES response_envelopes (id)
                            ON DELETE CASCADE,

    -- Opaque HMAC-derived lookup generated from the core session UUID and
    -- question-node UUID.
    answer_locator          BYTEA NOT NULL
                            CHECK (octet_length(answer_locator) = 32),

    -- Points to the canonical current revision.
    -- The foreign key is added after the revisions table is created.
    latest_revision_id      UUID NOT NULL,

    -- Required so revisions can use a composite foreign key and prove that
    -- their envelope matches the envelope of their logical answer.
    UNIQUE (id, envelope_id),

    -- Ensures one logical answer per question within one response session.
    UNIQUE (envelope_id, answer_locator)
);


CREATE TABLE response_answer_revisions (
    -- Random local UUID for one immutable historical revision.
    id                      UUID PRIMARY KEY,

    -- Links this immutable revision to its logical answer.
    answer_id               UUID NOT NULL,

    -- Repeated locally so nonce uniqueness can be enforced across every
    -- revision encrypted under the same session DEK.
    envelope_id             UUID NOT NULL,

    -- Increments whenever the participant saves a changed answer.
    revision_number         INTEGER NOT NULL
                            CHECK (revision_number > 0),

    -- Encrypted payload containing the real question-node UUID, answer state
    -- and answer value.
    ciphertext              BYTEA NOT NULL
                            CHECK (octet_length(ciphertext) >= 16),

    -- Fresh nonce generated for this individual encrypted revision.
    nonce                   BYTEA NOT NULL
                            CHECK (octet_length(nonce) = 12),


    -- Ensures envelope_id always matches the envelope of the logical answer.
    CONSTRAINT fk_revision_same_answer_envelope
        FOREIGN KEY (answer_id, envelope_id)
        REFERENCES response_answers (id, envelope_id)
        ON DELETE CASCADE,

    -- Required as the composite target of the latest-revision foreign key.
    -- The UUID id is already globally unique, but PostgreSQL needs the exact
    -- referenced column combination to be backed by a unique constraint.
    UNIQUE (id, answer_id),

    -- Ensures revision numbering cannot collide within one logical answer.
    UNIQUE (answer_id, revision_number),

    -- Prevents nonce reuse anywhere under the same session DEK, including
    -- earlier revisions of the same answer.
    UNIQUE (envelope_id, nonce)
);


-- Ensures the canonical pointer always references a revision belonging to the
-- same logical answer. Deferred validation allows the first logical answer and
-- its first revision to be inserted together inside one transaction.
ALTER TABLE response_answers
    ADD CONSTRAINT fk_latest_revision_same_answer
        FOREIGN KEY (latest_revision_id, id)
        REFERENCES response_answer_revisions (id, answer_id)
        DEFERRABLE INITIALLY DEFERRED;


CREATE INDEX idx_response_answers_envelope
    ON response_answers (envelope_id);

CREATE INDEX idx_response_answer_revisions_answer
    ON response_answer_revisions (answer_id);
```
