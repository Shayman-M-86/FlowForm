-- =========================================
-- FLOWFORM RESPONSE DATABASE SCHEMA (TIGHTENED)
-- =========================================
-- Purpose:
-- - stores sensitive submission payloads separately from the core app database
-- - designed to work with platform-managed or customer-managed Postgres databases
--
-- Notes:
-- - no foreign keys back to the core database because this is a separate database
-- - core_submission_id links this record back to survey_submissions.id in the core DB
-- - question_key ties answers to the frozen survey version used at submission time
-- - database checks below tighten answer shape validation, but backend validation against
--   the frozen compiled_schema must still be treated as the final authority

-- =========================================
-- HELPERS
-- =========================================

CREATE OR REPLACE FUNCTION jsonb_has_exact_keys(data JSONB, expected_keys TEXT[])
RETURNS BOOLEAN AS $$
    SELECT
        COALESCE(
            ARRAY(SELECT key FROM jsonb_each(data) ORDER BY key),
            ARRAY[]::TEXT[]
        )
        =
        COALESCE(
            ARRAY(SELECT key FROM unnest(expected_keys) AS key ORDER BY key),
            ARRAY[]::TEXT[]
        );
$$ LANGUAGE sql IMMUTABLE;

CREATE OR REPLACE FUNCTION jsonb_array_is_text_array(data JSONB)
RETURNS BOOLEAN AS $$
    SELECT
        jsonb_typeof(data) = 'array'
        AND NOT EXISTS (
            SELECT 1
            FROM jsonb_array_elements(data) AS elem
            WHERE jsonb_typeof(elem) <> 'string'
        );
$$ LANGUAGE sql IMMUTABLE;

CREATE OR REPLACE FUNCTION jsonb_is_scalar_or_null(data JSONB)
RETURNS BOOLEAN AS $$
    SELECT jsonb_typeof(data) IN ('string', 'number', 'boolean', 'null');
$$ LANGUAGE sql IMMUTABLE;

CREATE OR REPLACE FUNCTION jsonb_matching_matches_valid(data JSONB)
RETURNS BOOLEAN AS $$
    SELECT
        jsonb_typeof(data) = 'array'
        AND NOT EXISTS (
            SELECT 1
            FROM jsonb_array_elements(data) AS elem
            WHERE jsonb_typeof(elem) <> 'object'
               OR NOT jsonb_has_exact_keys(elem, ARRAY['left_id', 'right_id'])
               OR jsonb_typeof(elem->'left_id') <> 'string'
               OR jsonb_typeof(elem->'right_id') <> 'string'
        );
$$ LANGUAGE sql IMMUTABLE;

-- =========================================
-- SUBMISSIONS
-- =========================================

CREATE TABLE submissions (
    id BIGSERIAL PRIMARY KEY,
    core_submission_id BIGINT NOT NULL UNIQUE,
    survey_id BIGINT NOT NULL,
    survey_version_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL,
    pseudonymous_subject_id UUID,
    is_anonymous BOOLEAN NOT NULL DEFAULT FALSE,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_submissions_metadata_is_object
        CHECK (metadata IS NULL OR jsonb_typeof(metadata) = 'object')
);

-- =========================================
-- SUBMISSION ANSWERS
-- =========================================
-- answer_value is JSONB because answer shapes differ by question family.
-- Examples:
-- choice:   {"selected": ["a2"]}
-- field:    {"value": "name@example.com"}
-- matching: {"matches": [{"left_id": "c1", "right_id": "r1"}]}
-- rating:   {"value": 8}

CREATE TABLE submission_answers (
    id BIGSERIAL PRIMARY KEY,
    submission_id BIGINT NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    question_key TEXT NOT NULL,
    answer_family TEXT NOT NULL,
    answer_value JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_submission_answers_answer_family_valid
        CHECK (answer_family IN ('choice', 'field', 'matching', 'rating')),

    CONSTRAINT ck_submission_answers_answer_value_is_object
        CHECK (jsonb_typeof(answer_value) = 'object'),

    CONSTRAINT ck_submission_answers_choice_shape_valid
        CHECK (
            answer_family <> 'choice'
            OR (
                jsonb_has_exact_keys(answer_value, ARRAY['selected'])
                AND jsonb_array_is_text_array(answer_value->'selected')
            )
        ),

    CONSTRAINT ck_submission_answers_field_shape_valid 
        CHECK (
            answer_family <> 'field'
            OR (
                jsonb_has_exact_keys (answer_value, ARRAY['value'])
                AND jsonb_is_scalar_or_null (answer_value -> 'value')
            )
        ),

    CONSTRAINT ck_submission_answers_matching_shape_valid
    CHECK (
        answer_family <> 'matching'
        OR (
            jsonb_has_exact_keys(answer_value, ARRAY['matches'])
            AND jsonb_matching_matches_valid(answer_value->'matches')
        )
    ),

    CONSTRAINT ck_submission_answers_rating_shape_valid
        CHECK (
            answer_family <> 'rating'
            OR (
                jsonb_has_exact_keys(answer_value, ARRAY['value'])
                AND jsonb_typeof(answer_value->'value') = 'number'
            )
        ),

    CONSTRAINT uq_submission_answers_question
        UNIQUE (submission_id, question_key)
);
-- =========================================
-- SUBMISSION EVENTS
-- =========================================
-- Useful for debugging async delivery / write failures / retries.

CREATE TABLE submission_events (
    id BIGSERIAL PRIMARY KEY,
    submission_id BIGINT NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    event_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_submission_events_event_payload_is_object
        CHECK (event_payload IS NULL OR jsonb_typeof(event_payload) = 'object')
);

-- =========================================
-- INDEXES
-- =========================================

CREATE INDEX idx_submissions_survey ON submissions(survey_id);
CREATE INDEX idx_submissions_survey_version ON submissions(survey_version_id);
CREATE INDEX idx_submissions_project ON submissions(project_id);
CREATE INDEX idx_submissions_pseudonymous_subject ON submissions(pseudonymous_subject_id);
CREATE INDEX idx_submissions_submitted_at ON submissions(submitted_at);

CREATE INDEX idx_submission_answers_submission ON submission_answers(submission_id);
CREATE INDEX idx_submission_answers_question_key ON submission_answers(question_key);
CREATE INDEX idx_submission_answers_answer_family ON submission_answers(answer_family);
CREATE INDEX idx_submission_answers_answer_value_gin ON submission_answers USING GIN (answer_value);

CREATE INDEX idx_submission_events_submission ON submission_events(submission_id);
CREATE INDEX idx_submission_events_type ON submission_events(event_type);
