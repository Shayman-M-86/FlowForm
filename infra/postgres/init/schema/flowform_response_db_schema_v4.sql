-- =========================================
-- SESSION AND RESPONSE ENCRYPTION
-- =========================================
-- Anonymous encrypted envelopes, logical answers, and append-only answer
-- revisions. See docs/session-response-encryption/ for the full design.
--
-- Notes:
-- - No foreign keys back to the core database. session_locator and
--   answer_locator are HMAC-derived lookups; this database does not know
--   who the respondent is.
-- - response_answer_revisions is append-only; response_answers.latest_revision_id
--   is the canonical pointer.

-- =========================================
-- HELPERS
-- =========================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION prevent_response_answer_revision_updates()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Cannot update immutable response answer revisions';
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- =========================================
-- RESPONSE ENVELOPES
-- =========================================

CREATE TABLE response_envelopes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Hidden cross-database lookup. Derived from the core
    -- submission_sessions.id using an external linkage secret.
    session_locator BYTEA NOT NULL,

    -- Identifies the external linkage-secret version used to derive the
    -- session locator and answer locators.
    linkage_key_version SMALLINT NOT NULL,

    -- Encrypted copy of the session-specific Data Encryption Key.
    -- One DEK protects all revisions belonging to this envelope.
    wrapped_dek BYTEA NOT NULL,

    -- Immutable ARN of the KMS-managed Key Encryption Key used to wrap the DEK.
    kms_key_arn TEXT NOT NULL,

    -- Identifies the KMS encryption context version used when wrapping the DEK.
    kms_context_version SMALLINT NOT NULL,

    -- Identifies the local authenticated-encryption format and algorithm.
    crypto_version SMALLINT NOT NULL,

    CONSTRAINT uq_response_envelopes_session_locator
        UNIQUE (session_locator),

    CONSTRAINT ck_response_envelopes_session_locator_len
        CHECK (octet_length(session_locator) = 32),

    CONSTRAINT ck_response_envelopes_linkage_key_version_valid
        CHECK (linkage_key_version > 0),

    CONSTRAINT ck_response_envelopes_wrapped_dek_len
        CHECK (octet_length(wrapped_dek) > 0),

    CONSTRAINT ck_response_envelopes_kms_key_arn_len
        CHECK (char_length(btrim(kms_key_arn)) BETWEEN 1 AND 2048),

    CONSTRAINT ck_response_envelopes_crypto_version_valid
        CHECK (crypto_version > 0),

    CONSTRAINT ck_response_envelopes_kms_context_version_valid
        CHECK (kms_context_version > 0)
);

-- =========================================
-- RESPONSE ANSWERS
-- =========================================

CREATE TABLE response_answers (
    -- Stable local ID for one logical question answer.
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Groups this logical answer under one anonymous response envelope.
    envelope_id UUID NOT NULL REFERENCES response_envelopes(id) ON DELETE CASCADE,

    -- Opaque HMAC-derived lookup generated from the core session UUID and
    -- question-node UUID.
    answer_locator BYTEA NOT NULL,

    -- Points to the canonical current revision.
    -- The foreign key is added after the revisions table is created.
    latest_revision_id UUID NOT NULL,

    CONSTRAINT ck_response_answers_answer_locator_len
        CHECK (octet_length(answer_locator) = 32),

    -- Required so revisions can use a composite foreign key and prove that
    -- their envelope matches the envelope of their logical answer.
    CONSTRAINT uq_response_answers_id_envelope_id
        UNIQUE (id, envelope_id),

    -- Ensures one logical answer per question within one response session.
    CONSTRAINT uq_response_answers_envelope_id_answer_locator
        UNIQUE (envelope_id, answer_locator)
);

-- =========================================
-- RESPONSE ANSWER REVISIONS
-- =========================================

CREATE TABLE response_answer_revisions (
    -- Random local UUID for one immutable historical revision.
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Links this immutable revision to its logical answer.
    answer_id UUID NOT NULL,

    -- Repeated locally so nonce uniqueness can be enforced across every
    -- revision encrypted under the same session DEK.
    envelope_id UUID NOT NULL,

    -- Increments whenever the participant saves a changed answer.
    revision_number INTEGER NOT NULL,

    -- Encrypted payload containing the real question-node UUID, answer state
    -- and answer value.
    ciphertext BYTEA NOT NULL,

    -- Fresh nonce generated for this individual encrypted revision.
    nonce BYTEA NOT NULL,

    -- Client-supplied idempotency key for the save request that produced
    -- this revision.
    client_mutation_id UUID NOT NULL,

    CONSTRAINT ck_response_answer_revisions_revision_number_valid
        CHECK (revision_number > 0),

    CONSTRAINT ck_response_answer_revisions_ciphertext_len
        CHECK (octet_length(ciphertext) >= 16),

    CONSTRAINT ck_response_answer_revisions_nonce_len
        CHECK (octet_length(nonce) = 12),

    -- Ensures envelope_id always matches the envelope of the logical answer.
    CONSTRAINT fk_response_answer_revisions_answer_same_envelope
        FOREIGN KEY (answer_id, envelope_id)
        REFERENCES response_answers (id, envelope_id)
        ON DELETE CASCADE,

    -- Required as the composite target of the latest-revision foreign key.
    -- The UUID id is already globally unique, but PostgreSQL needs the exact
    -- referenced column combination to be backed by a unique constraint.
    CONSTRAINT uq_response_answer_revisions_id_answer_id
        UNIQUE (id, answer_id),

    -- Ensures revision numbering cannot collide within one logical answer.
    CONSTRAINT uq_response_answer_revisions_answer_id_revision_number
        UNIQUE (answer_id, revision_number),

    -- Prevents nonce reuse anywhere under the same session DEK, including
    -- earlier revisions of the same answer.
    CONSTRAINT uq_response_answer_revisions_envelope_id_nonce
        UNIQUE (envelope_id, nonce),

    -- Enforces idempotent saves per logical answer.
    CONSTRAINT uq_response_answer_revisions_answer_id_client_mutation_id
        UNIQUE (answer_id, client_mutation_id)
);

-- Ensures the canonical pointer always references a revision belonging to
-- the same logical answer. Deferred validation allows the first logical
-- answer and its first revision to be inserted together inside one
-- transaction.
ALTER TABLE response_answers
    ADD CONSTRAINT fk_response_answers_latest_revision_same_answer
        FOREIGN KEY (latest_revision_id, id)
        REFERENCES response_answer_revisions (id, answer_id)
        DEFERRABLE INITIALLY DEFERRED;

-- =========================================
-- TRIGGERS
-- =========================================
-- Revisions are immutable once written. Deletes remain allowed so retention
-- and privacy purges can remove an envelope and its dependent rows.

CREATE TRIGGER trg_response_answer_revisions_prevent_update
BEFORE UPDATE ON response_answer_revisions
FOR EACH ROW EXECUTE FUNCTION prevent_response_answer_revision_updates();

-- =========================================
-- INDEXES
-- =========================================

CREATE INDEX idx_response_answers_envelope ON response_answers(envelope_id);
CREATE INDEX idx_response_answer_revisions_answer ON response_answer_revisions(answer_id);
