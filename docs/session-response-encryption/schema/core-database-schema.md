# Core Database Schema

Core database tables for project-level respondent identities, respondent
sessions, and core-side submission analytics events.

These tables extend the existing FlowForm core schema. They reference existing
`projects`, `users`, `surveys`, `survey_versions`, `response_stores`,
`survey_links`, and `survey_questions` rows. Raw answers are not stored here.

## Project subject relation

`project_subjects` is the current relation for project-scoped respondent
identity. A project subject is the stable core-side participant record that a
submission session may optionally point at.

Use the columns carefully:

- `project_subjects.id` is the internal UUID foreign key target used by
  `submission_sessions.project_subject_id`.
- `project_subjects.subject_code` is the stable project-scoped participant
  code.
- `project_subject_identities` attaches revocable email or authenticated-user
  identities to a subject.
- `project_subject_tokens` stores reusable recognition-token hashes for a
  subject.
- `survey_links.assigned_subject_id` can pin a bearer link to a project
  subject.
- `submission_sessions.project_subject_id` is nullable. Null means the session
  is fully anonymous at the core identity layer.
- `subject_ip_observations` stores identifying core metadata tied to a subject
  and/or a submission session. It is never copied to the response DB.

```sql
CREATE TABLE project_subjects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    subject_code TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_project_subjects_project_id_id
        UNIQUE (project_id, id),

    CONSTRAINT uq_project_subjects_project_id_subject_code
        UNIQUE (project_id, subject_code),

    CONSTRAINT ck_project_subjects_subject_code_len
        CHECK (
            subject_code = btrim(subject_code)
            AND char_length(subject_code) BETWEEN 1 AND 128
        )
);

CREATE TABLE project_subject_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    project_subject_id UUID NOT NULL,
    identity_type TEXT NOT NULL,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    normalized_email TEXT,
    verification_status TEXT NOT NULL DEFAULT 'unverified',
    verified_at TIMESTAMPTZ,
    attached_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,

    CONSTRAINT fk_project_subject_identities_subject_same_project
        FOREIGN KEY (project_id, project_subject_id)
        REFERENCES project_subjects(project_id, id)
        ON DELETE CASCADE,

    CONSTRAINT ck_project_subject_identities_identity_type_valid
        CHECK (identity_type IN ('email', 'authenticated_user')),

    CONSTRAINT ck_project_subject_identities_identity_value_valid
        CHECK (
            (
                identity_type = 'email'
                AND normalized_email IS NOT NULL
                AND user_id IS NULL
            )
            OR
            (
                identity_type = 'authenticated_user'
                AND user_id IS NOT NULL
                AND normalized_email IS NULL
            )
        ),

    CONSTRAINT ck_project_subject_identities_verification_status_valid
        CHECK (verification_status IN ('unverified', 'verified')),

    CONSTRAINT ck_project_subject_identities_verified_at_consistent
        CHECK ((verification_status = 'verified') = (verified_at IS NOT NULL)),

    CONSTRAINT ck_project_subject_identities_normalized_email_valid
        CHECK (
            normalized_email IS NULL
            OR (
                normalized_email = lower(btrim(normalized_email))
                AND char_length(normalized_email) BETWEEN 3 AND 320
            )
        ),

    CONSTRAINT ck_project_subject_identities_verified_at_after_attached_at
        CHECK (
            verified_at IS NULL
            OR verified_at >= attached_at
        ),

    CONSTRAINT ck_project_subject_identities_revoked_at_after_attached_at
        CHECK (
            revoked_at IS NULL
            OR revoked_at >= attached_at
        )
);

CREATE UNIQUE INDEX uq_project_subject_identities_active_user
    ON project_subject_identities (project_id, user_id)
    WHERE (
        identity_type = 'authenticated_user'
        AND user_id IS NOT NULL
        AND revoked_at IS NULL
    );

CREATE UNIQUE INDEX uq_project_subject_identities_subject_active_email
    ON project_subject_identities (project_subject_id, normalized_email)
    WHERE (
        identity_type = 'email'
        AND normalized_email IS NOT NULL
        AND revoked_at IS NULL
    );

CREATE UNIQUE INDEX uq_project_subject_identities_project_verified_email
    ON project_subject_identities (project_id, normalized_email)
    WHERE (
        identity_type = 'email'
        AND normalized_email IS NOT NULL
        AND verification_status = 'verified'
        AND revoked_at IS NULL
    );

CREATE TABLE project_subject_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    project_subject_id UUID NOT NULL,
    token_hash TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_project_subject_tokens_token_hash
        UNIQUE (token_hash),

    CONSTRAINT fk_project_subject_tokens_subject_same_project
        FOREIGN KEY (project_id, project_subject_id)
        REFERENCES project_subjects(project_id, id)
        ON DELETE CASCADE,

    CONSTRAINT ck_project_subject_tokens_token_hash_format
        CHECK (token_hash ~ '^[0-9a-f]{64}$'),

    CONSTRAINT ck_project_subject_tokens_expires_at_after_created_at
        CHECK (expires_at > created_at),

    CONSTRAINT ck_project_subject_tokens_last_used_at_after_created_at
        CHECK (
            last_used_at IS NULL
            OR last_used_at >= created_at
        ),

    CONSTRAINT ck_project_subject_tokens_revoked_at_after_created_at
        CHECK (
            revoked_at IS NULL
            OR revoked_at >= created_at
        ),

    CONSTRAINT ck_project_subject_tokens_last_used_before_revocation
        CHECK (
            revoked_at IS NULL
            OR last_used_at IS NULL
            OR last_used_at <= revoked_at
        )
);

ALTER TABLE survey_links
    ADD COLUMN assigned_subject_id UUID,
    ADD CONSTRAINT fk_survey_links_assigned_subject_same_project
        FOREIGN KEY (project_id, assigned_subject_id)
        REFERENCES project_subjects(project_id, id)
        ON DELETE RESTRICT,
    ADD CONSTRAINT ck_survey_links_used_at_requires_assignment
        CHECK (
            used_at IS NULL
            OR assigned_email IS NOT NULL
            OR assigned_subject_id IS NOT NULL
        );

CREATE TABLE submission_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    survey_id BIGINT NOT NULL,
    survey_version_id BIGINT NOT NULL,
    response_store_id BIGINT NOT NULL REFERENCES response_stores(id) ON DELETE RESTRICT,
    link_id BIGINT REFERENCES survey_links(id) ON DELETE SET NULL,
    project_subject_id UUID REFERENCES project_subjects(id) ON DELETE SET NULL,
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

    CONSTRAINT uq_submission_sessions_project_id_id
        UNIQUE (project_id, id),

    CONSTRAINT uq_submission_sessions_id_project_subject_id
        UNIQUE (id, project_subject_id),

    CONSTRAINT ck_submission_sessions_browser_session_token_hash_len
        CHECK (length(browser_session_token_hash) >= 32),

    CONSTRAINT ck_submission_sessions_linkage_key_version_valid
        CHECK (linkage_key_version > 0),

    CONSTRAINT ck_submission_sessions_session_status_valid
        CHECK (session_status IN ('in_progress', 'completed', 'abandoned')),

    CONSTRAINT ck_submission_sessions_completed_at_consistent
        CHECK ((session_status = 'completed') = (completed_at IS NOT NULL)),

    CONSTRAINT ck_submission_sessions_completed_at_after_started_at
        CHECK (
            completed_at IS NULL
            OR completed_at >= started_at
        ),

    CONSTRAINT ck_submission_sessions_expires_at_after_started_at
        CHECK (expires_at > started_at),

    CONSTRAINT ck_submission_sessions_last_activity_at_after_started_at
        CHECK (last_activity_at >= started_at),

    CONSTRAINT ck_submission_sessions_completed_before_last_activity
        CHECK (
            completed_at IS NULL
            OR completed_at <= last_activity_at
        ),

    CONSTRAINT fk_submission_sessions_survey_same_project
        FOREIGN KEY (project_id, survey_id)
        REFERENCES surveys(project_id, id)
        ON DELETE CASCADE,

    CONSTRAINT fk_submission_sessions_version_same_survey
        FOREIGN KEY (survey_id, survey_version_id)
        REFERENCES survey_versions(survey_id, id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_submission_sessions_store_same_project
        FOREIGN KEY (project_id, response_store_id)
        REFERENCES response_stores(project_id, id),

    CONSTRAINT fk_submission_sessions_link_same_survey
        FOREIGN KEY (survey_id, link_id)
        REFERENCES survey_links(survey_id, id),

    CONSTRAINT fk_submission_sessions_project_subject_same_project
        FOREIGN KEY (project_id, project_subject_id)
        REFERENCES project_subjects(project_id, id)
);

CREATE TABLE submission_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    survey_version_id BIGINT NOT NULL,
    event_type TEXT NOT NULL,
    question_node_id UUID REFERENCES survey_questions(id) ON DELETE SET NULL,
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

    CONSTRAINT fk_submission_events_question_node_same_version
        FOREIGN KEY (survey_version_id, question_node_id)
        REFERENCES survey_questions(survey_version_id, id)
);

CREATE TABLE subject_ip_observations (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    project_subject_id UUID REFERENCES project_subjects(id) ON DELETE CASCADE,
    submission_session_id UUID REFERENCES submission_sessions(id) ON DELETE CASCADE,

    ip_address INET NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_subject_ip_observations_has_owner
        CHECK (
            project_subject_id IS NOT NULL
            OR submission_session_id IS NOT NULL
        ),

    CONSTRAINT fk_subject_ip_observations_subject_same_project
        FOREIGN KEY (project_id, project_subject_id)
        REFERENCES project_subjects(project_id, id),

    CONSTRAINT fk_subject_ip_observations_session_same_project
        FOREIGN KEY (project_id, submission_session_id)
        REFERENCES submission_sessions(project_id, id),

    CONSTRAINT fk_subject_ip_observations_session_subject_match
        FOREIGN KEY (submission_session_id, project_subject_id)
        REFERENCES submission_sessions(id, project_subject_id)
);

CREATE INDEX ix_project_subjects_project ON project_subjects(project_id);
CREATE INDEX ix_project_subject_identities_subject ON project_subject_identities(project_subject_id);
CREATE INDEX ix_project_subject_identities_user ON project_subject_identities(user_id);
CREATE INDEX ix_project_subject_tokens_subject ON project_subject_tokens(project_subject_id);
CREATE INDEX ix_project_subject_tokens_active_expiry ON project_subject_tokens(expires_at)
    WHERE revoked_at IS NULL;

CREATE INDEX ix_submission_sessions_project ON submission_sessions(project_id);
CREATE INDEX ix_submission_sessions_survey ON submission_sessions(survey_id);
CREATE INDEX ix_submission_sessions_survey_version ON submission_sessions(survey_version_id);
CREATE INDEX ix_submission_sessions_store ON submission_sessions(response_store_id);
CREATE INDEX ix_submission_sessions_link ON submission_sessions(link_id)
    WHERE link_id IS NOT NULL;
CREATE INDEX ix_submission_sessions_project_subject ON submission_sessions(project_subject_id)
    WHERE project_subject_id IS NOT NULL;
CREATE INDEX ix_submission_sessions_last_activity ON submission_sessions(session_status, last_activity_at);
CREATE INDEX ix_submission_sessions_expires_at ON submission_sessions(expires_at);

CREATE INDEX ix_submission_events_session_received_at ON submission_events(session_id, received_at);
CREATE INDEX ix_submission_events_survey_version ON submission_events(survey_version_id);
CREATE INDEX ix_submission_events_question_node ON submission_events(question_node_id)
    WHERE question_node_id IS NOT NULL;

CREATE INDEX ix_subject_ip_observations_project_observed_at
    ON subject_ip_observations(project_id, observed_at DESC);
CREATE INDEX ix_subject_ip_observations_subject_observed_at
    ON subject_ip_observations(project_subject_id, observed_at DESC)
    WHERE project_subject_id IS NOT NULL;
CREATE INDEX ix_subject_ip_observations_session_observed_at
    ON subject_ip_observations(submission_session_id, observed_at DESC)
    WHERE submission_session_id IS NOT NULL;
CREATE INDEX ix_subject_ip_observations_ip_observed_at
    ON subject_ip_observations(ip_address, observed_at DESC);
```
