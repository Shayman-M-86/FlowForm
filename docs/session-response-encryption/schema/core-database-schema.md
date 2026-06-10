# Core Database Schema

Core database tables for respondent sessions, subject association, and submission events.

```sql
CREATE TYPE submission_event_type AS ENUM (
    'session_started',
    'question_viewed',
    'answer_saved',
    'session_completed'
);

CREATE TYPE submission_session_status AS ENUM (
    'in_progress',
    'completed',
    'abandoned'
);

CREATE TABLE links (
    id UUID PRIMARY KEY
);

CREATE TABLE project_subjects (
    id                          UUID PRIMARY KEY,

    project_id                  UUID NOT NULL,

    pseudonymous_subject_id     TEXT NOT NULL,

    user_id                     UUID NULL,

    created_at                  TIMESTAMPTZ NOT NULL,

    -- Prevents the same pseudonymous participant ID from being registered
    -- twice within one project.
    CONSTRAINT uq_project_subjects_project_pseudonymous_subject
        UNIQUE (project_id, pseudonymous_subject_id),

    -- Prevents the same known user from receiving multiple subject records
    -- within one project. Multiple NULL values remain allowed.
    CONSTRAINT uq_project_subjects_project_user
        UNIQUE (project_id, user_id)
);


CREATE TABLE submission_sessions (
    -- Random core-database UUID representing one survey attempt. Used as the
    -- private input when deriving the response-side session_locator.
    id                          UUID PRIMARY KEY,

    -- Optional reference to the link used to access the survey. May remain NULL
    -- when the session was created through another access method.
    link_id                     UUID NULL
                                REFERENCES links (id),

    -- Optional participant association. Remains NULL for fully anonymous survey
    -- sessions.
    project_subject_id          UUID NULL
                                REFERENCES project_subjects (id),

    survey_version_id           UUID NOT NULL,

    -- Hash of the random token held by the respondent's browser. Allows an
    -- in-progress session to be resumed without storing the raw browser token.
    browser_session_token_hash  BYTEA NOT NULL UNIQUE,

    -- Identifies which external linkage-secret version the backend must use
    -- when deriving the response-side session_locator and answer_locator values.
    linkage_key_version         SMALLINT NOT NULL DEFAULT 1,

    session_status              submission_session_status NOT NULL,
    started_at                  TIMESTAMPTZ NOT NULL,
    completed_at                TIMESTAMPTZ NULL,
    expires_at                  TIMESTAMPTZ NOT NULL,
    last_activity_at            TIMESTAMPTZ NOT NULL
);


CREATE TABLE submission_events (
    -- Random local UUID representing one analytics event.
    id                  UUID PRIMARY KEY,

    -- Associates the event with one survey session. Events are deleted
    -- automatically if the parent session is removed.
    session_id          UUID NOT NULL
                        REFERENCES submission_sessions (id)
                        ON DELETE CASCADE,

    event_type          submission_event_type NOT NULL,

    -- Identifies the relevant survey question for question_viewed and
    -- answer_saved events. Remains NULL for session-level events. This
    -- plaintext value stays only in the core database.
    question_node_id    UUID NULL,

    received_at         TIMESTAMPTZ NOT NULL
);


CREATE INDEX idx_submission_sessions_last_activity
    ON submission_sessions (session_status, last_activity_at);

CREATE INDEX idx_submission_events_session_received_at
    ON submission_events (session_id, received_at);
```
