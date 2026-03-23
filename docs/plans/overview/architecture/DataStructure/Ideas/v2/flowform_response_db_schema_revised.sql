-- =========================================
-- FLOWFORM RESPONSE DATABASE SCHEMA (REVISED)
-- =========================================
-- Purpose:
-- - stores sensitive submission payloads separately from the core app database
-- - designed to work with platform-managed or customer-managed Postgres databases
--
-- Notes:
-- - no foreign keys back to the core database because this is a separate database
-- - core_submission_id links this record back to survey_submissions.id in the core DB
-- - question_key ties answers to the frozen survey version used at submission time

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
    CHECK (metadata IS NULL OR jsonb_typeof(metadata) = 'object')
);

-- =========================================
-- SUBMISSION ANSWERS
-- =========================================
-- answer_value is JSONB because answer shapes differ by question family.
-- Examples:
-- choice:   {"selected_option_ids": ["a2"]}
-- field:    {"value": "name@example.com"}
-- matching: {"pairs": [{"left_id": "c1", "right_id": "r1"}]}
-- rating:   {"value": 8}

CREATE TABLE submission_answers (
    id BIGSERIAL PRIMARY KEY,
    submission_id BIGINT NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    question_key TEXT NOT NULL,
    answer_family TEXT NOT NULL,
    answer_value JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (answer_family IN ('choice', 'field', 'matching', 'rating')),
    CHECK (jsonb_typeof(answer_value) = 'object'),
    UNIQUE (submission_id, question_key)
);

-- =========================================
-- OPTIONAL SUBMISSION EVENTS
-- =========================================
-- Useful for debugging async delivery / write failures / retries.

CREATE TABLE submission_events (
    id BIGSERIAL PRIMARY KEY,
    submission_id BIGINT NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    event_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
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
