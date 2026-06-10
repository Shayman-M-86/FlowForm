# Core Database Schema

Core database tables for project-level participant identities, respondent
sessions, and core-side submission analytics events.

These tables extend the existing FlowForm core schema. They reference existing
`projects`, `users`, `surveys`, `survey_versions`, `response_stores`,
`survey_links`, and `survey_questions` rows. Raw answers are not stored here.

```sql
CREATE TABLE project_subjects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    pseudonymous_subject_id TEXT NOT NULL,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_project_subjects_project_id_id
        UNIQUE (project_id, id),

    CONSTRAINT uq_project_subjects_project_id_pseudonymous_subject_id
        UNIQUE (project_id, pseudonymous_subject_id),

    CONSTRAINT uq_project_subjects_project_id_user_id
        UNIQUE (project_id, user_id),

    CONSTRAINT ck_project_subjects_pseudonymous_subject_id_len
        CHECK (char_length(btrim(pseudonymous_subject_id)) BETWEEN 1 AND 128)
);

CREATE TABLE submission_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id BIGINT NOT NULL,
    survey_id BIGINT NOT NULL,
    survey_version_id BIGINT NOT NULL,
    response_store_id BIGINT NOT NULL,
    link_id BIGINT,
    project_subject_id UUID,
    browser_session_token_hash BYTEA NOT NULL,
    linkage_key_version SMALLINT NOT NULL DEFAULT 1,
    session_status TEXT NOT NULL DEFAULT 'in_progress',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_submission_sessions_browser_session_token_hash
        UNIQUE (browser_session_token_hash),

    CONSTRAINT uq_submission_sessions_id_survey_version_id
        UNIQUE (id, survey_version_id),

    CONSTRAINT ck_submission_sessions_browser_session_token_hash_len
        CHECK (length(browser_session_token_hash) >= 32),

    CONSTRAINT ck_submission_sessions_linkage_key_version_valid
        CHECK (linkage_key_version > 0),

    CONSTRAINT ck_submission_sessions_session_status_valid
        CHECK (session_status IN ('in_progress', 'completed', 'abandoned')),

    CONSTRAINT ck_submission_sessions_completed_requires_completed_at
        CHECK (session_status <> 'completed' OR completed_at IS NOT NULL),

    CONSTRAINT ck_submission_sessions_completed_at_after_started_at
        CHECK (
            completed_at IS NULL
            OR completed_at >= started_at
        ),

    CONSTRAINT ck_submission_sessions_expires_at_after_started_at
        CHECK (expires_at > started_at),

    CONSTRAINT fk_submission_sessions_survey_same_project
        FOREIGN KEY (project_id, survey_id)
        REFERENCES surveys(project_id, id)
        ON DELETE CASCADE,

    CONSTRAINT fk_submission_sessions_version_same_survey
        FOREIGN KEY (survey_id, survey_version_id)
        REFERENCES survey_versions(survey_id, id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_submission_sessions_store
        FOREIGN KEY (response_store_id)
        REFERENCES response_stores(id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_submission_sessions_store_same_project
        FOREIGN KEY (project_id, response_store_id)
        REFERENCES response_stores(project_id, id),

    CONSTRAINT fk_submission_sessions_link
        FOREIGN KEY (link_id)
        REFERENCES survey_links(id)
        ON DELETE SET NULL,

    CONSTRAINT fk_submission_sessions_link_same_survey
        FOREIGN KEY (survey_id, link_id)
        REFERENCES survey_links(survey_id, id),

    CONSTRAINT fk_submission_sessions_project_subject
        FOREIGN KEY (project_subject_id)
        REFERENCES project_subjects(id)
        ON DELETE SET NULL,

    CONSTRAINT fk_submission_sessions_project_subject_same_project
        FOREIGN KEY (project_id, project_subject_id)
        REFERENCES project_subjects(project_id, id)
);

CREATE TABLE submission_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    survey_version_id BIGINT NOT NULL,
    event_type TEXT NOT NULL,
    question_node_id UUID,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_submission_events_event_type_valid
        CHECK (event_type IN ('session_started', 'question_viewed', 'answer_saved', 'session_completed')),

    CONSTRAINT ck_submission_events_question_required_for_question_events
        CHECK (
            event_type NOT IN ('question_viewed', 'answer_saved')
            OR question_node_id IS NOT NULL
        ),

    CONSTRAINT ck_submission_events_question_absent_for_session_events
        CHECK (
            event_type NOT IN ('session_started', 'session_completed')
            OR question_node_id IS NULL
        ),

    CONSTRAINT fk_submission_events_session_version
        FOREIGN KEY (session_id, survey_version_id)
        REFERENCES submission_sessions(id, survey_version_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_submission_events_question_node
        FOREIGN KEY (question_node_id)
        REFERENCES survey_questions(id)
        ON DELETE SET NULL,

    CONSTRAINT fk_submission_events_question_node_same_version
        FOREIGN KEY (survey_version_id, question_node_id)
        REFERENCES survey_questions(survey_version_id, id)
);

CREATE INDEX idx_project_subjects_project ON project_subjects(project_id);
CREATE INDEX idx_project_subjects_user ON project_subjects(user_id);

CREATE INDEX idx_submission_sessions_project ON submission_sessions(project_id);
CREATE INDEX idx_submission_sessions_survey ON submission_sessions(survey_id);
CREATE INDEX idx_submission_sessions_survey_version ON submission_sessions(survey_version_id);
CREATE INDEX idx_submission_sessions_store ON submission_sessions(response_store_id);
CREATE INDEX idx_submission_sessions_link ON submission_sessions(link_id);
CREATE INDEX idx_submission_sessions_project_subject ON submission_sessions(project_subject_id);
CREATE INDEX idx_submission_sessions_last_activity ON submission_sessions(session_status, last_activity_at);
CREATE INDEX idx_submission_sessions_expires_at ON submission_sessions(expires_at);

CREATE INDEX idx_submission_events_session_received_at ON submission_events(session_id, received_at);
CREATE INDEX idx_submission_events_question_node ON submission_events(question_node_id);
```
