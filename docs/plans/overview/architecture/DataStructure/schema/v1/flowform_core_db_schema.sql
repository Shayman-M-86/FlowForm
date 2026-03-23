-- =========================================
-- FLOWFORM CORE DATABASE SCHEMA
-- =========================================
-- Purpose:
-- - stores application, RBAC, survey definition, publishing, and submission registry data
-- - does NOT store raw survey answers
--
-- Notes:
-- - survey definition is versioned so old submissions stay tied to a frozen structure
-- - response storage is configurable per project/survey
-- - raw answers live in a separate response database

-- =========================================
-- USERS
-- =========================================

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    auth0_user_id TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- =========================================
-- PROJECTS
-- =========================================

CREATE TABLE projects (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- =========================================
-- PROJECT MEMBERSHIPS
-- =========================================

CREATE TABLE project_memberships (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    role_id BIGINT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE (user_id, project_id),
    CHECK (status IN ('active', 'invited'))
);

-- =========================================
-- PERMISSIONS
-- =========================================

CREATE TABLE permissions (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

-- =========================================
-- PROJECT ROLES
-- =========================================

CREATE TABLE project_roles (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    is_system_role BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, name)
);

CREATE TABLE project_role_permissions (
    role_id BIGINT NOT NULL REFERENCES project_roles(id) ON DELETE CASCADE,
    permission_id BIGINT NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

ALTER TABLE project_memberships
ADD CONSTRAINT fk_project_memberships_role
FOREIGN KEY (role_id) REFERENCES project_roles(id) ON DELETE SET NULL;

-- =========================================
-- RESPONSE STORES
-- =========================================
-- Defines where a project's or survey's responses should be written.
-- For customer-managed databases, encrypted secrets should NOT be stored as plain JSON.
-- In production, store a reference to Secrets Manager / Vault rather than raw credentials.

CREATE TABLE response_stores (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    store_type TEXT NOT NULL,
    connection_reference JSONB NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CHECK (store_type IN ('platform_postgres', 'external_postgres')),
    UNIQUE (project_id, name)
);

-- =========================================
-- SURVEYS
-- =========================================

CREATE TABLE surveys (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    visibility TEXT NOT NULL DEFAULT 'private',
    allow_public_responses BOOLEAN NOT NULL DEFAULT FALSE,
    public_slug TEXT UNIQUE,
    default_response_store_id BIGINT REFERENCES response_stores(id) ON DELETE SET NULL,
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CHECK (status IN ('draft', 'published', 'archived')),
    CHECK (visibility IN ('private', 'link_only', 'public'))
);

-- =========================================
-- SURVEY VERSIONS
-- =========================================
-- Each published structure should be frozen here.
-- Draft edits create or update a version record.

CREATE TABLE survey_versions (
    id BIGSERIAL PRIMARY KEY,
    survey_id BIGINT NOT NULL REFERENCES surveys(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    compiled_schema JSONB,
    published_at TIMESTAMPTZ,
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CHECK (status IN ('draft', 'published', 'archived')),
    UNIQUE (survey_id, version_number)
);

-- Optional convenience: one currently active published version per survey.
CREATE UNIQUE INDEX uq_survey_versions_one_published
    ON survey_versions (survey_id)
    WHERE status = 'published' AND deleted_at IS NULL;

-- =========================================
-- SURVEY QUESTIONS
-- =========================================

CREATE TABLE survey_questions (
    id BIGSERIAL PRIMARY KEY,
    survey_version_id BIGINT NOT NULL REFERENCES survey_versions(id) ON DELETE CASCADE,
    question_key TEXT NOT NULL,
    question_schema JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE (survey_version_id, question_key)
);

-- =========================================
-- SURVEY RULES
-- =========================================

CREATE TABLE survey_rules (
    id BIGSERIAL PRIMARY KEY,
    survey_version_id BIGINT NOT NULL REFERENCES survey_versions(id) ON DELETE CASCADE,
    rule_key TEXT NOT NULL,
    rule_schema JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE (survey_version_id, rule_key)
);

-- =========================================
-- SURVEY SCORING RULES
-- =========================================

CREATE TABLE survey_scoring_rules (
    id BIGSERIAL PRIMARY KEY,
    survey_version_id BIGINT NOT NULL REFERENCES survey_versions(id) ON DELETE CASCADE,
    scoring_key TEXT NOT NULL,
    scoring_schema JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE (survey_version_id, scoring_key)
);

-- =========================================
-- SURVEY ROLES (OVERRIDE MODEL)
-- =========================================

CREATE TABLE survey_roles (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, name)
);

CREATE TABLE survey_role_permissions (
    role_id BIGINT NOT NULL REFERENCES survey_roles(id) ON DELETE CASCADE,
    permission_id BIGINT NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE survey_membership_roles (
    survey_id BIGINT NOT NULL REFERENCES surveys(id) ON DELETE CASCADE,
    membership_id BIGINT NOT NULL REFERENCES project_memberships(id) ON DELETE CASCADE,
    role_id BIGINT NOT NULL REFERENCES survey_roles(id) ON DELETE CASCADE,
    PRIMARY KEY (survey_id, membership_id)
);

-- =========================================
-- PUBLIC LINKS
-- =========================================

CREATE TABLE survey_public_links (
    id BIGSERIAL PRIMARY KEY,
    survey_id BIGINT NOT NULL REFERENCES surveys(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    allow_response BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================================
-- PSEUDONYMOUS SUBJECT MAPPINGS
-- =========================================
-- Maps an internal user to a stable pseudonymous identifier for a project.
-- This identifier can be written to the response DB instead of the real user_id.

CREATE TABLE response_subject_mappings (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pseudonymous_subject_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (project_id, user_id),
    UNIQUE (project_id, pseudonymous_subject_id)
);

-- =========================================
-- SURVEY SUBMISSION REGISTRY
-- =========================================
-- Metadata only. Raw answers are stored in the separate response database.

CREATE TABLE survey_submissions (
    id BIGSERIAL PRIMARY KEY,
    survey_id BIGINT NOT NULL REFERENCES surveys(id) ON DELETE CASCADE,
    survey_version_id BIGINT NOT NULL REFERENCES survey_versions(id) ON DELETE RESTRICT,
    response_store_id BIGINT REFERENCES response_stores(id) ON DELETE SET NULL,
    submitted_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    public_link_id BIGINT REFERENCES survey_public_links(id) ON DELETE SET NULL,
    pseudonymous_subject_id UUID,
    external_submission_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    is_anonymous BOOLEAN NOT NULL DEFAULT FALSE,
    started_at TIMESTAMPTZ,
    submitted_at TIMESTAMPTZ,
    last_delivery_attempt_at TIMESTAMPTZ,
    delivery_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (status IN ('pending', 'stored', 'failed'))
);

-- =========================================
-- AUDIT LOG
-- =========================================

CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id BIGINT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================================
-- INDEXES
-- =========================================

CREATE INDEX idx_project_memberships_user ON project_memberships(user_id);
CREATE INDEX idx_project_memberships_project ON project_memberships(project_id);

CREATE INDEX idx_response_stores_project ON response_stores(project_id);
CREATE INDEX idx_response_subject_mappings_project_user ON response_subject_mappings(project_id, user_id);

CREATE INDEX idx_surveys_project ON surveys(project_id);
CREATE INDEX idx_surveys_slug ON surveys(public_slug);
CREATE INDEX idx_surveys_default_response_store ON surveys(default_response_store_id);

CREATE INDEX idx_survey_versions_survey ON survey_versions(survey_id);
CREATE INDEX idx_survey_questions_version ON survey_questions(survey_version_id);
CREATE INDEX idx_survey_rules_version ON survey_rules(survey_version_id);
CREATE INDEX idx_survey_scoring_rules_version ON survey_scoring_rules(survey_version_id);

CREATE INDEX idx_survey_public_links_survey ON survey_public_links(survey_id);
CREATE INDEX idx_survey_public_links_token ON survey_public_links(token);

CREATE INDEX idx_survey_submissions_survey ON survey_submissions(survey_id);
CREATE INDEX idx_survey_submissions_version ON survey_submissions(survey_version_id);
CREATE INDEX idx_survey_submissions_store ON survey_submissions(response_store_id);
CREATE INDEX idx_survey_submissions_submitted_by ON survey_submissions(submitted_by_user_id);
CREATE INDEX idx_survey_submissions_pseudonymous_subject ON survey_submissions(pseudonymous_subject_id);
CREATE INDEX idx_survey_submissions_status ON survey_submissions(status);

CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
