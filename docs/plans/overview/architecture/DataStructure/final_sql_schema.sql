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

-- =========================================
-- ROLE PERMISSIONS
-- =========================================

CREATE TABLE project_role_permissions (
    role_id BIGINT NOT NULL REFERENCES project_roles(id) ON DELETE CASCADE,
    permission_id BIGINT NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- Add FK after roles table exists
ALTER TABLE project_memberships
ADD CONSTRAINT fk_project_memberships_role
FOREIGN KEY (role_id) REFERENCES project_roles(id) ON DELETE SET NULL;

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
    created_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CHECK (status IN ('draft', 'published', 'archived')),
    CHECK (visibility IN ('private', 'link_only', 'public')),
);

-- =========================================
-- SURVEY QUESTIONS
-- =========================================

CREATE TABLE survey_questions (
    id BIGSERIAL PRIMARY KEY,
    survey_id BIGINT NOT NULL REFERENCES surveys (id) ON DELETE CASCADE,
    question_key TEXT NOT NULL,
    question_schema JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE (survey_id, question_key)
);

-- =========================================
-- SURVEY RULES
-- =========================================

CREATE TABLE survey_rules (
    id BIGSERIAL PRIMARY KEY,
    survey_id BIGINT NOT NULL REFERENCES surveys (id) ON DELETE CASCADE,
    rule_key TEXT NOT NULL,
    rule_schema JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE (survey_id, rule_key)
);

-- =========================================
-- SURVEY SCORING RULES
-- =========================================

CREATE TABLE survey_scoring_rules (
    id BIGSERIAL PRIMARY KEY,
    survey_id BIGINT NOT NULL REFERENCES surveys (id) ON DELETE CASCADE,
    scoring_key TEXT NOT NULL,
    scoring_schema JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE (survey_id, scoring_key)
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
-- RESPONSES
-- =========================================

CREATE TABLE survey_responses (
    id BIGSERIAL PRIMARY KEY,
    survey_id BIGINT NOT NULL REFERENCES surveys(id) ON DELETE CASCADE,
    submitted_by_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    public_link_id BIGINT REFERENCES survey_public_links(id) ON DELETE SET NULL,
    is_anonymous BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
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

CREATE INDEX idx_surveys_project ON surveys(project_id);
CREATE INDEX idx_surveys_slug ON surveys(public_slug);

CREATE INDEX idx_survey_public_links_survey ON survey_public_links(survey_id);
CREATE INDEX idx_survey_public_links_token ON survey_public_links(token);

CREATE INDEX idx_survey_responses_survey ON survey_responses(survey_id);

CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
