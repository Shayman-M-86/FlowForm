-- =========================================
-- FLOWFORM CORE DATABASE SCHEMA (REVISED)
-- =========================================
-- Purpose:
-- - stores application, RBAC, survey definition, publishing, and submission registry data
-- - does NOT store raw survey answers
--
-- Design notes:
-- - hard delete is used for normal entities such as projects, surveys, stores, roles, memberships, and links
-- - only survey_versions use soft delete because old compiled versions may be required to interpret stored responses
-- - extra composite foreign keys are used to prevent cross-project and cross-survey mismatches

-- =========================================
-- HELPERS
-- =========================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =========================================
-- USERS
-- =========================================

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    auth0_user_id TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================================
-- PROJECTS
-- =========================================

CREATE TABLE projects (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
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
    UNIQUE (project_id, id),
    UNIQUE (project_id, name)
);

CREATE TABLE project_role_permissions (
    role_id BIGINT NOT NULL REFERENCES project_roles(id) ON DELETE CASCADE,
    permission_id BIGINT NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
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
    CHECK (status IN ('active', 'invited')),
    UNIQUE (user_id, project_id),
    UNIQUE (project_id, id),
    CONSTRAINT fk_project_memberships_role
        FOREIGN KEY (role_id)
        REFERENCES project_roles(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_project_memberships_role_same_project
        FOREIGN KEY (project_id, role_id)
        REFERENCES project_roles(project_id, id)
);

-- =========================================
-- RESPONSE STORES
-- =========================================
-- Defines where a project's or survey's responses should be written.
-- For customer-managed databases, store only a reference to a secret, not raw credentials.

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
    CHECK (store_type IN ('platform_postgres', 'external_postgres')),
    CHECK (jsonb_typeof(connection_reference) = 'object'),
    UNIQUE (project_id, id),
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
    default_response_store_id BIGINT,
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (status IN ('draft', 'published', 'archived')),
    CHECK (visibility IN ('private', 'link_only', 'public')),
    CHECK (
        allow_public_responses = FALSE
        OR visibility IN ('link_only', 'public')
    ),
    CHECK (
        visibility <> 'public'
        OR public_slug IS NOT NULL
    ),
    CHECK (
        public_slug IS NULL
        OR visibility IN ('link_only', 'public')
    ),
    UNIQUE (project_id, id),
    CONSTRAINT fk_surveys_default_store
        FOREIGN KEY (default_response_store_id)
        REFERENCES response_stores(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_surveys_default_store_same_project
        FOREIGN KEY (project_id, default_response_store_id)
        REFERENCES response_stores(project_id, id)
);

-- =========================================
-- SURVEY VERSIONS
-- =========================================
-- Each published structure is frozen here.
-- Only this table uses soft delete because old compiled versions may be needed later.

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
    CHECK (version_number > 0),
    CHECK (
        status <> 'published'
        OR (compiled_schema IS NOT NULL AND published_at IS NOT NULL)
    ),
    UNIQUE (survey_id, id),
    UNIQUE (survey_id, version_number)
);

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
    CHECK (jsonb_typeof(question_schema) = 'object'),
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
    CHECK (jsonb_typeof(rule_schema) = 'object'),
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
    CHECK (jsonb_typeof(scoring_schema) = 'object'),
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
    UNIQUE (project_id, id),
    UNIQUE (project_id, name)
);

CREATE TABLE survey_role_permissions (
    role_id BIGINT NOT NULL REFERENCES survey_roles(id) ON DELETE CASCADE,
    permission_id BIGINT NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE survey_membership_roles (
    project_id BIGINT NOT NULL,
    survey_id BIGINT NOT NULL,
    membership_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (survey_id, membership_id),
    CONSTRAINT fk_survey_membership_roles_survey_same_project
        FOREIGN KEY (project_id, survey_id)
        REFERENCES surveys(project_id, id)
        ON DELETE CASCADE,
    CONSTRAINT fk_survey_membership_roles_membership_same_project
        FOREIGN KEY (project_id, membership_id)
        REFERENCES project_memberships(project_id, id)
        ON DELETE CASCADE,
    CONSTRAINT fk_survey_membership_roles_role_same_project
        FOREIGN KEY (project_id, role_id)
        REFERENCES survey_roles(project_id, id)
        ON DELETE CASCADE
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
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (survey_id, id)
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
    UNIQUE (project_id, id),
    UNIQUE (project_id, user_id),
    UNIQUE (project_id, pseudonymous_subject_id)
);

-- =========================================
-- SURVEY SUBMISSION REGISTRY
-- =========================================
-- Metadata only. Raw answers are stored in the separate response database.

CREATE TABLE survey_submissions (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL,
    survey_id BIGINT NOT NULL,
    survey_version_id BIGINT NOT NULL,
    response_store_id BIGINT,
    submitted_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    public_link_id BIGINT,
    pseudonymous_subject_id UUID,
    external_submission_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    is_anonymous BOOLEAN NOT NULL DEFAULT FALSE,
    started_at TIMESTAMPTZ,
    submitted_at TIMESTAMPTZ,
    last_delivery_attempt_at TIMESTAMPTZ,
    delivery_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (status IN ('pending', 'stored', 'failed')),
    CHECK (
        submitted_at IS NULL
        OR started_at IS NULL
        OR submitted_at >= started_at
    ),
    CONSTRAINT fk_survey_submissions_survey_same_project
        FOREIGN KEY (project_id, survey_id)
        REFERENCES surveys(project_id, id)
        ON DELETE CASCADE,
    CONSTRAINT fk_survey_submissions_version_same_survey
        FOREIGN KEY (survey_id, survey_version_id)
        REFERENCES survey_versions(survey_id, id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_survey_submissions_store
        FOREIGN KEY (response_store_id)
        REFERENCES response_stores(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_survey_submissions_store_same_project
        FOREIGN KEY (project_id, response_store_id)
        REFERENCES response_stores(project_id, id),
    CONSTRAINT fk_survey_submissions_public_link
        FOREIGN KEY (public_link_id)
        REFERENCES survey_public_links(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_survey_submissions_public_link_same_survey
        FOREIGN KEY (survey_id, public_link_id)
        REFERENCES survey_public_links(survey_id, id),
    CONSTRAINT fk_survey_submissions_subject_same_project
        FOREIGN KEY (project_id, pseudonymous_subject_id)
        REFERENCES response_subject_mappings(project_id, pseudonymous_subject_id)
        ON DELETE RESTRICT
);

CREATE UNIQUE INDEX uq_survey_submissions_external_submission_id
    ON survey_submissions (response_store_id, external_submission_id)
    WHERE external_submission_id IS NOT NULL;

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
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (metadata IS NULL OR jsonb_typeof(metadata) = 'object')
);

-- =========================================
-- TRIGGERS
-- =========================================

CREATE TRIGGER trg_response_stores_updated_at
BEFORE UPDATE ON response_stores
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_surveys_updated_at
BEFORE UPDATE ON surveys
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_survey_versions_updated_at
BEFORE UPDATE ON survey_versions
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_survey_questions_updated_at
BEFORE UPDATE ON survey_questions
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_survey_rules_updated_at
BEFORE UPDATE ON survey_rules
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_survey_scoring_rules_updated_at
BEFORE UPDATE ON survey_scoring_rules
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =========================================
-- INDEXES
-- =========================================

CREATE INDEX idx_project_memberships_user ON project_memberships(user_id);
CREATE INDEX idx_project_memberships_project ON project_memberships(project_id);
CREATE INDEX idx_project_memberships_role ON project_memberships(role_id);

CREATE INDEX idx_response_stores_project ON response_stores(project_id);
CREATE INDEX idx_response_subject_mappings_project_user ON response_subject_mappings(project_id, user_id);
CREATE INDEX idx_response_subject_mappings_project_subject ON response_subject_mappings(project_id, pseudonymous_subject_id);

CREATE INDEX idx_surveys_project ON surveys(project_id);
CREATE INDEX idx_surveys_slug ON surveys(public_slug);
CREATE INDEX idx_surveys_default_response_store ON surveys(default_response_store_id);

CREATE INDEX idx_survey_versions_survey ON survey_versions(survey_id);
CREATE INDEX idx_survey_versions_status ON survey_versions(status);
CREATE INDEX idx_survey_questions_version ON survey_questions(survey_version_id);
CREATE INDEX idx_survey_rules_version ON survey_rules(survey_version_id);
CREATE INDEX idx_survey_scoring_rules_version ON survey_scoring_rules(survey_version_id);

CREATE INDEX idx_survey_membership_roles_project ON survey_membership_roles(project_id);
CREATE INDEX idx_survey_membership_roles_membership ON survey_membership_roles(membership_id);
CREATE INDEX idx_survey_membership_roles_role ON survey_membership_roles(role_id);

CREATE INDEX idx_survey_public_links_survey ON survey_public_links(survey_id);
CREATE INDEX idx_survey_public_links_token ON survey_public_links(token);

CREATE INDEX idx_survey_submissions_project ON survey_submissions(project_id);
CREATE INDEX idx_survey_submissions_survey ON survey_submissions(survey_id);
CREATE INDEX idx_survey_submissions_version ON survey_submissions(survey_version_id);
CREATE INDEX idx_survey_submissions_store ON survey_submissions(response_store_id);
CREATE INDEX idx_survey_submissions_submitted_by ON survey_submissions(submitted_by_user_id);
CREATE INDEX idx_survey_submissions_pseudonymous_subject ON survey_submissions(pseudonymous_subject_id);
CREATE INDEX idx_survey_submissions_status ON survey_submissions(status);
CREATE INDEX idx_survey_submissions_submitted_at ON survey_submissions(submitted_at);

CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
