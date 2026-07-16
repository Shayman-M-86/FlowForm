-- =========================================
-- SESSION AND RESPONSE ENCRYPTION
-- =========================================
-- Anonymous encrypted envelopes and current encrypted answer rows.
-- See docs/session-encryption/ for the broader design.
--
-- Notes:
-- - No foreign keys back to the core database. session_locator and
--   answer_locator are HMAC-derived lookups; this database does not know
--   who the respondent is.

-- =========================================
-- HELPERS
-- =========================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;

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
    -- This DEK is wrapped locally by the survey branch key, not directly by KMS.
    wrapped_session_dek BYTEA NOT NULL,

    -- Identifies the local authenticated-encryption format and algorithm.
    crypto_version SMALLINT NOT NULL,

    CONSTRAINT uq_response_envelopes_session_locator
        UNIQUE (session_locator),

    CONSTRAINT ck_response_envelopes_session_locator_len
        CHECK (octet_length(session_locator) = 32),

    CONSTRAINT ck_response_envelopes_linkage_key_version_valid
        CHECK (linkage_key_version > 0),

    CONSTRAINT ck_response_envelopes_wrapped_session_dek_len
        CHECK (octet_length(wrapped_session_dek) > 0),

    CONSTRAINT ck_response_envelopes_crypto_version_valid
        CHECK (crypto_version > 0)
);

-- =========================================
-- RESPONSE ANSWERS
-- =========================================

CREATE TABLE response_answers (
    -- Opaque HMAC-derived lookup generated from the core answer slot UUID.
    answer_locator BYTEA NOT NULL,

    -- Groups this current answer under one anonymous response envelope.
    envelope_id UUID NOT NULL,

    -- Encrypted payload containing the real question-node UUID, answer state
    -- and answer value.
    ciphertext BYTEA NOT NULL,

    -- Fresh nonce generated for this encrypted current answer.
    nonce BYTEA NOT NULL,

    -- Client-supplied idempotency key for the save request that produced
    -- the current answer row.
    client_mutation_id UUID,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_response_answers
        PRIMARY KEY (answer_locator),

    CONSTRAINT fk_response_answers_envelope_id__response_envelopes
        FOREIGN KEY (envelope_id)
        REFERENCES response_envelopes (id)
        ON DELETE CASCADE,

    CONSTRAINT ck_response_answers_answer_locator_len
        CHECK (octet_length(answer_locator) = 32),

    CONSTRAINT ck_response_answers_nonce_len
        CHECK (octet_length(nonce) = 12),

    CONSTRAINT ck_response_answers_ciphertext_non_empty
        CHECK (octet_length(ciphertext) > 0),

    -- Prevents nonce reuse under the same session DEK.
    CONSTRAINT uq_response_answers_envelope_id_nonce
        UNIQUE (envelope_id, nonce)
);

-- =========================================
-- INDEXES
-- =========================================

CREATE INDEX idx_response_answers_envelope ON response_answers(envelope_id);
