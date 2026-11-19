-- Active: 1774882034658@@localhost@5432@flowform_core@core_app
-- =========================================
-- FLOWFORM CORE DATABASE MOCK DATA
-- =========================================
-- Purpose:
-- - seeds realistic mock data for local development and testing
-- - matches flowform_core_db_schema_v4.sql
-- - uses explicit UUIDs for submission_sessions so the response DB seed can
--   derive matching session_locator values
--
-- - Survey versions contain V2 definitions with stable field UUIDs.
--
-- Safe to run on an empty schema.

BEGIN;

-- =========================================
-- USERS
-- =========================================

INSERT INTO users (id, public_id, auth0_user_id, email, display_name, created_at, platform_admin, email_verified) VALUES
    (1, 'A1x9Kq43', 'auth0|flowform-admin',   'alex@flowform.dev',   'Alex Carter',   NOW() - INTERVAL '40 days', TRUE,  TRUE),
    (2, 'M7s2Qa23', 'auth0|project-owner',    'maya@acme.dev',       'Maya Singh',    NOW() - INTERVAL '35 days', FALSE, TRUE),
    (3, 'L4t8Np34', 'auth0|project-editor',   'liam@acme.dev',       'Liam Turner',   NOW() - INTERVAL '30 days', FALSE, TRUE),
    (4, 'Z9w3Vr64', 'auth0|project-viewer',   'zoe@acme.dev',        'Zoe Walker',    NOW() - INTERVAL '28 days', FALSE, TRUE),
    (5, 'N2b6Hx25', 'auth0|research-owner',   'noah@beta.dev',       'Noah Bennett',  NOW() - INTERVAL '24 days', FALSE, TRUE),
    (6, 'G5p1Yu15', 'auth0|public-link-user', 'guest@example.test',  'Public Guest',  NOW() - INTERVAL '10 days', FALSE, TRUE),
    (7, 'U8n4Tq71', 'auth0|unverified-user',  'unverified@example.test', 'Pat Unverified', NOW() - INTERVAL '2 days', FALSE, FALSE);

-- =========================================
-- PROJECTS
-- =========================================

INSERT INTO projects (id, name, slug, created_by_user_id, created_at) VALUES
    (1, 'Acme Employee Feedback', 'acme-employee-feedback', 2, NOW() - INTERVAL '34 days'),
    (2, 'Beta Product Research',  'beta-product-research',  5, NOW() - INTERVAL '22 days');

-- =========================================
-- PERMISSIONS
-- =========================================


-- =========================================
-- PROJECT ROLES
-- =========================================

INSERT INTO project_roles (id, project_id, name, is_system_role, created_at) VALUES
    (1, 1, 'Owner',  TRUE,  NOW() - INTERVAL '34 days'),
    (2, 1, 'Editor', TRUE,  NOW() - INTERVAL '33 days'),
    (3, 1, 'Viewer', TRUE,  NOW() - INTERVAL '33 days'),
    (4, 2, 'Owner',  TRUE,  NOW() - INTERVAL '22 days'),
    (5, 2, 'Analyst', TRUE, NOW() - INTERVAL '21 days');

INSERT INTO project_role_permissions (role_id, permission_id)
SELECT r.role_id, p.id
FROM (VALUES
    (1, 'project:edit'),
    (1, 'project:delete'),
    (1, 'project:manage_members'),
    (1, 'project:manage_roles'),
    (1, 'survey:view'),
    (1, 'survey:create'),
    (1, 'survey:edit'),
    (1, 'survey:delete'),
    (1, 'survey:publish'),
    (1, 'survey:archive'),
    (1, 'submission:view'),

    (2, 'survey:view'),
    (2, 'survey:create'),
    (2, 'survey:edit'),
    (2, 'survey:publish'),
    (2, 'submission:view'),

    (3, 'survey:view'),
    (3, 'submission:view'),

    (4, 'project:edit'),
    (4, 'project:delete'),
    (4, 'project:manage_members'),
    (4, 'project:manage_roles'),
    (4, 'survey:view'),
    (4, 'survey:create'),
    (4, 'survey:edit'),
    (4, 'survey:delete'),
    (4, 'survey:publish'),
    (4, 'survey:archive'),
    (4, 'submission:view'),

    (5, 'survey:view'),
    (5, 'submission:view')
) AS r(role_id, perm_name)
JOIN permissions p ON p.name = r.perm_name;

-- =========================================
-- PROJECT MEMBERSHIPS
-- =========================================

INSERT INTO project_memberships (id, user_id, project_id, role_id, status, created_at) VALUES
    (1, 2, 1, 1, 'active',  NOW() - INTERVAL '34 days'),
    (2, 3, 1, 2, 'active',  NOW() - INTERVAL '31 days'),
    (3, 4, 1, 3, 'active', NOW() - INTERVAL '20 days'),
    (4, 5, 2, 4, 'active',  NOW() - INTERVAL '22 days'),
    (5, 1, 2, 5, 'active',  NOW() - INTERVAL '18 days');

-- =========================================
-- RESPONSE STORES
-- =========================================

INSERT INTO response_stores (id, project_id, name, store_type, connection_reference, is_active, created_by_user_id, created_at, updated_at) VALUES
    (1, 1, 'Platform Primary', 'platform_postgres', $json${"driver":"postgres","database":"flowform_response","schema":"public"}$json$::jsonb, TRUE, 2, NOW() - INTERVAL '34 days', NOW() - INTERVAL '2 days'),
    (2, 1, 'Client Warehouse', 'external_postgres', $json${"secret_ref":"acme/prod/warehouse","host":"warehouse.acme.internal","database":"survey_results"}$json$::jsonb, TRUE, 2, NOW() - INTERVAL '15 days', NOW() - INTERVAL '1 day'),
    (3, 2, 'Platform Analytics', 'platform_postgres', $json${"driver":"postgres","database":"flowform_response_beta","schema":"public"}$json$::jsonb, TRUE, 5, NOW() - INTERVAL '22 days', NOW() - INTERVAL '12 hours');

-- =========================================
-- SURVEYS
-- =========================================

INSERT INTO surveys (id, project_id, title, visibility, public_slug, default_response_store_id, published_version_id, created_by_user_id, created_at, updated_at) VALUES
    (1, 1, 'Employee Engagement Pulse', 'link_only', NULL, 1, NULL, 2, NOW() - INTERVAL '28 days', NOW() - INTERVAL '2 days'),
    (2, 1, 'Manager Effectiveness Review', 'private', NULL, 2, NULL, 3, NOW() - INTERVAL '18 days', NOW() - INTERVAL '18 hours'),
    (3, 2, 'Beta Signup Experience', 'public', 'beta-signup-experience', 3, NULL, 5, NOW() - INTERVAL '14 days', NOW() - INTERVAL '6 hours');

-- =========================================
-- SURVEY VERSIONS
-- =========================================
-- Insert the versions as drafts before loading definitions and publishing.

INSERT INTO survey_versions (id, survey_id, version_number, status, published_at, created_by_user_id, created_at, updated_at, deleted_at) VALUES
    (1, 1, 1, 'draft', NULL, 2, NOW() - INTERVAL '27 days', NOW() - INTERVAL '27 days', NULL),
    (2, 1, 2, 'draft', NULL, 3, NOW() - INTERVAL '7 days',  NOW() - INTERVAL '7 days',  NULL),
    (3, 2, 1, 'draft', NULL, 3, NOW() - INTERVAL '17 days', NOW() - INTERVAL '17 days', NULL),
    (4, 3, 1, 'draft', NULL, 5, NOW() - INTERVAL '13 days', NOW() - INTERVAL '13 days', NULL),
    (5, 3, 2, 'draft', NULL, 5, NOW() - INTERVAL '3 days',  NOW() - INTERVAL '3 days',  NULL);

UPDATE survey_versions AS v
SET definition = fixture.definition
FROM (VALUES
    (1, $json${
        "id": "employee-engagement",
        "versionId": 1,
        "revision": 1,
        "title": "Employee Engagement Pulse",
        "projectName": "Acme Employee Feedback",
        "status": "draft",
        "document": {"sections": [{"id": "main", "title": "Employee Engagement Pulse", "blocks": [
            {"id": "engagement_score", "type": "input", "field": {"id": "engagement_score", "uuid": "00000000-0000-0000-0000-000000000001", "prompt": "How engaged do you feel at work?", "interaction": {"kind": "rating", "presentation": "slider"}, "answerSpec": {"type": "integer", "constraints": {"min": 1, "max": 10}, "required": true}}},
            {"id": "team_support", "type": "input", "field": {"id": "team_support", "uuid": "00000000-0000-0000-0000-000000000002", "prompt": "How supported do you feel by your team?", "interaction": {"kind": "single_choice", "presentation": "radio", "options": [{"id": "very_supported", "uuid": "ec1d5ef8-756b-5a36-9f9c-98cf6c2585b8", "label": "Very supported"}, {"id": "somewhat_supported", "uuid": "c6e7cd3c-21c6-5dfb-b648-396f814e6862", "label": "Somewhat supported"}, {"id": "not_supported", "uuid": "f65dde98-5297-5c40-b88f-1d26209a5a9f", "label": "Not supported"}]}, "answerSpec": {"type": "choice", "required": true}}}
        ]}]}
    }$json$::jsonb),
    (2, $json${
        "id": "employee-engagement",
        "versionId": 2,
        "revision": 1,
        "title": "Employee Engagement Pulse",
        "projectName": "Acme Employee Feedback",
        "status": "published",
        "document": {"sections": [{"id": "main", "title": "Employee Engagement Pulse", "blocks": [
            {"id": "engagement_score", "type": "input", "field": {"id": "engagement_score", "uuid": "00000000-0000-0000-0000-000000000003", "prompt": "How engaged do you feel at work?", "interaction": {"kind": "rating", "presentation": "slider"}, "answerSpec": {"type": "integer", "constraints": {"min": 1, "max": 10}, "required": true}}},
            {"id": "team_support", "type": "input", "field": {"id": "team_support", "uuid": "00000000-0000-0000-0000-000000000004", "prompt": "How supported do you feel by your team?", "interaction": {"kind": "single_choice", "presentation": "radio", "options": [{"id": "very_supported", "uuid": "7d319775-c118-5ca2-83a9-3ecd50bb6bf3", "label": "Very supported"}, {"id": "somewhat_supported", "uuid": "097ada5d-4eec-51a7-97e4-f7bbe7efa336", "label": "Somewhat supported"}, {"id": "not_supported", "uuid": "bb61b09a-4cbf-5cc4-bf28-00fcdb1a8655", "label": "Not supported"}]}, "answerSpec": {"type": "choice", "required": true}}},
            {"id": "manager_feedback", "type": "input", "field": {"id": "manager_feedback", "uuid": "00000000-0000-0000-0000-000000000005", "prompt": "What is one thing your manager could do better?", "interaction": {"kind": "long_text", "placeholder": "Share one practical improvement"}, "answerSpec": {"type": "string", "required": true}, "behaviour": {"visibility": {"mode": "conditional", "condition": {"fieldUuid": "00000000-0000-0000-0000-000000000003", "operator": "less_than", "value": 7}}}}}
        ]}]}
    }$json$::jsonb),
    (3, $json${
        "id": "manager-effectiveness",
        "versionId": 3,
        "revision": 1,
        "title": "Manager Effectiveness Review",
        "projectName": "Acme Employee Feedback",
        "status": "draft",
        "document": {"sections": [{"id": "main", "title": "Manager Effectiveness Review", "blocks": [
            {"id": "clarity_rating", "type": "input", "field": {"id": "clarity_rating", "uuid": "00000000-0000-0000-0000-000000000007", "prompt": "My manager sets clear expectations.", "interaction": {"kind": "rating", "presentation": "slider"}, "answerSpec": {"type": "integer", "constraints": {"min": 1, "max": 5}, "required": true}}},
            {"id": "coaching_examples", "type": "input", "field": {"id": "coaching_examples", "uuid": "00000000-0000-0000-0000-000000000008", "prompt": "Share an example of good coaching.", "interaction": {"kind": "long_text", "placeholder": "Describe a specific example"}, "answerSpec": {"type": "string", "required": false}}}
        ]}]}
    }$json$::jsonb),
    (4, $json${
        "id": "beta-signup",
        "versionId": 4,
        "revision": 1,
        "title": "Beta Signup Experience",
        "projectName": "Beta Product Research",
        "status": "draft",
        "document": {"sections": [{"id": "main", "title": "Beta Signup Experience", "blocks": [
            {"id": "signup_ease", "type": "input", "field": {"id": "signup_ease", "uuid": "00000000-0000-0000-0000-000000000009", "prompt": "How easy was signup?", "interaction": {"kind": "rating", "presentation": "slider"}, "answerSpec": {"type": "integer", "constraints": {"min": 1, "max": 10}, "required": true}}},
            {"id": "feature_interest", "type": "input", "field": {"id": "feature_interest", "uuid": "00000000-0000-0000-0000-000000000010", "prompt": "Which feature interested you most?", "interaction": {"kind": "single_choice", "presentation": "radio", "options": [{"id": "automation", "uuid": "4bf83e1a-7b04-5cd7-a7bc-fc9158082033", "label": "Automation"}, {"id": "analytics", "uuid": "27f562dc-9a37-5819-9870-8ed6b3ddd40a", "label": "Analytics"}]}, "answerSpec": {"type": "choice", "required": true}}}
        ]}]}
    }$json$::jsonb),
    (5, $json${
        "id": "beta-signup",
        "versionId": 5,
        "revision": 1,
        "title": "Beta Signup Experience",
        "projectName": "Beta Product Research",
        "status": "published",
        "document": {"sections": [{"id": "main", "title": "Beta Signup Experience", "blocks": [
            {"id": "signup_ease", "type": "input", "field": {"id": "signup_ease", "uuid": "00000000-0000-0000-0000-000000000011", "prompt": "How easy was signup?", "interaction": {"kind": "rating", "presentation": "slider"}, "answerSpec": {"type": "integer", "constraints": {"min": 1, "max": 10}, "required": true}}},
            {"id": "feature_interest", "type": "input", "field": {"id": "feature_interest", "uuid": "00000000-0000-0000-0000-000000000012", "prompt": "Which feature interested you most?", "interaction": {"kind": "single_choice", "presentation": "radio", "options": [{"id": "automation", "uuid": "c7198ca4-e18d-5595-8541-7888c31f5e0b", "label": "Automation"}, {"id": "analytics", "uuid": "3a1d8028-21ec-55fe-aeef-57402bacf866", "label": "Analytics"}]}, "answerSpec": {"type": "choice", "required": true}}},
            {"id": "followup_email", "type": "input", "field": {"id": "followup_email", "uuid": "00000000-0000-0000-0000-000000000013", "prompt": "Leave your email if you want follow-up.", "interaction": {"kind": "short_text", "placeholder": "name@example.com"}, "answerSpec": {"type": "string", "required": false}, "behaviour": {"visibility": {"mode": "conditional", "condition": {"fieldUuid": "00000000-0000-0000-0000-000000000011", "operator": "greater_than", "value": 7}}}}}
        ]}]}
    }$json$::jsonb)
) AS fixture(version_id, definition)
WHERE v.id = fixture.version_id;

-- =========================================
-- PROJECT SUBJECTS
-- =========================================
-- subject_code is the stable project-scoped pseudonymous participant code.
-- It is NOT derived from a user id or email. Authenticated-user and email
-- identities attach via project_subject_identities below.

INSERT INTO project_subjects (id, project_id, subject_code, created_at) VALUES
    ('11111111-1111-1111-1111-111111111111', 1, 'subj-acme-0001', NOW() - INTERVAL '25 days'),
    ('22222222-2222-2222-2222-222222222222', 1, 'subj-acme-0002', NOW() - INTERVAL '25 days'),
    ('33333333-3333-3333-3333-333333333333', 2, 'subj-beta-0001', NOW() - INTERVAL '11 days'),
    ('66666666-6666-6666-6666-666666666666', 1, 'subj-acme-0003', NOW() - INTERVAL '5 days');

-- =========================================
-- PROJECT SUBJECT IDENTITIES
-- =========================================
-- Revocable attachments. authenticated_user rows carry user_id; email rows
-- carry normalized_email. A subject may have both an account and an email
-- identity. At most one active authenticated_user per (project, user_id), and
-- at most one verified active owner per (project, normalized_email).

INSERT INTO project_subject_identities
    (id, project_id, project_subject_id, identity_type, user_id, normalized_email, verification_status, verified_at, attached_at) VALUES
    ('a1a1a1a1-0000-0000-0000-000000000001', 1, '11111111-1111-1111-1111-111111111111', 'authenticated_user', 2, 'maya@acme.dev', 'verified', NOW() - INTERVAL '25 days', NOW() - INTERVAL '25 days'),
    ('a1a1a1a1-0000-0000-0000-000000000002', 1, '22222222-2222-2222-2222-222222222222', 'authenticated_user', 3, 'liam@acme.dev', 'verified', NOW() - INTERVAL '25 days', NOW() - INTERVAL '25 days'),
    ('a1a1a1a1-0000-0000-0000-000000000003', 2, '33333333-3333-3333-3333-333333333333', 'authenticated_user', 5, 'noah@beta.dev', 'verified', NOW() - INTERVAL '11 days', NOW() - INTERVAL '11 days'),
    ('a1a1a1a1-0000-0000-0000-000000000004', 1, '66666666-6666-6666-6666-666666666666', 'email', NULL, 'guest@example.test', 'unverified', NULL, NOW() - INTERVAL '5 days');

-- =========================================
-- PROJECT SUBJECT TOKENS
-- =========================================
-- token_hash is a lowercase hex SHA-256 digest of the raw recognition token.

INSERT INTO project_subject_tokens
    (id, project_id, project_subject_id, token_hash, expires_at, last_used_at, created_at) VALUES
    ('b1b1b1b1-0000-0000-0000-000000000001', 1, '11111111-1111-1111-1111-111111111111', encode(digest('subject-token-acme-0001', 'sha256'), 'hex'), NOW() + INTERVAL '90 days', NOW() - INTERVAL '4 days', NOW() - INTERVAL '25 days'),
    ('b1b1b1b1-0000-0000-0000-000000000002', 2, '33333333-3333-3333-3333-333333333333', encode(digest('subject-token-beta-0001', 'sha256'), 'hex'), NOW() + INTERVAL '90 days', NULL, NOW() - INTERVAL '11 days');

-- =========================================
-- PROJECT PARTICIPANTS
-- =========================================
-- A subject participates in a project at most once. Assigned survey links
-- target a participant within the link's project.

-- Each participant carries a specific subject identity (authenticated_user here).
INSERT INTO project_participants (id, project_id, project_subject_id, identity_id, created_at) VALUES
    ('cccccccc-0000-0000-0000-000000000001', 1, '11111111-1111-1111-1111-111111111111', 'a1a1a1a1-0000-0000-0000-000000000001', NOW() - INTERVAL '25 days'),
    ('cccccccc-0000-0000-0000-000000000002', 2, '33333333-3333-3333-3333-333333333333', 'a1a1a1a1-0000-0000-0000-000000000003', NOW() - INTERVAL '11 days');

-- =========================================
-- PUBLIC LINKS
-- =========================================
-- project_id is stored directly so the database can prove link, survey, and
-- assigned participant share a project. link_type is one of general, private,
-- authenticated; private/authenticated links must be assigned to a participant
-- (which itself carries a subject + identity). assignment_source is always set
-- (manual | automated). The assigned email is derived by joining through the
-- participant's identity; it is not stored on survey_links.

INSERT INTO survey_links (id, project_id, survey_id, name, token, is_active, link_type, assignment_source, assigned_participant_id, expires_at, created_at) VALUES
    ('dddddddd-0000-0000-0000-000000000001', 1, 1, 'Acme pulse invite', 'acmepuls01-mock-token-0001', TRUE, 'authenticated', 'manual', 'cccccccc-0000-0000-0000-000000000001', NOW() + INTERVAL '30 days', NOW() - INTERVAL '5 days'),
    ('dddddddd-0000-0000-0000-000000000002', 2, 3, 'Beta signup invite', 'betasign02-mock-token-0002', TRUE, 'authenticated', 'automated', 'cccccccc-0000-0000-0000-000000000002', NOW() + INTERVAL '14 days', NOW() - INTERVAL '2 days');

-- =========================================
-- SUBMISSION SESSIONS
-- =========================================

-- Seed the linkage version used by the sample sessions.
INSERT INTO linkage_key_versions (version, aws_secret_id, aws_secret_version_id)
VALUES (1, 'flowform/local/mock-linkage', '00000000-0000-0000-0000-000000000001')
ON CONFLICT (version) DO NOTHING;

INSERT INTO submission_sessions (id, project_id, survey_id, survey_version_id, response_store_id, link_id, project_subject_id, browser_session_token_hash, linkage_key_version, session_status, started_at, completed_at, expires_at, last_activity_at) VALUES
    ('aaaaaaaa-0000-0000-0000-000000000001', 1, 1, 2, 1, NULL, '11111111-1111-1111-1111-111111111111', digest('session-token-0001', 'sha256'), 1, 'completed', NOW() - INTERVAL '4 days 15 minutes', NOW() - INTERVAL '4 days', NOW() - INTERVAL '4 days' + INTERVAL '7 days', NOW() - INTERVAL '4 days'),
    ('aaaaaaaa-0000-0000-0000-000000000002', 1, 1, 2, 1, 'dddddddd-0000-0000-0000-000000000001', '66666666-6666-6666-6666-666666666666', digest('session-token-0002', 'sha256'), 1, 'completed', NOW() - INTERVAL '3 days 20 minutes', NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days' + INTERVAL '7 days', NOW() - INTERVAL '3 days'),
    ('aaaaaaaa-0000-0000-0000-000000000003', 2, 3, 5, 3, NULL, NULL, digest('session-token-0003', 'sha256'), 1, 'abandoned', NOW() - INTERVAL '2 days 40 minutes', NULL, NOW() - INTERVAL '2 days 40 minutes' + INTERVAL '7 days', NOW() - INTERVAL '2 days 40 minutes'),
    ('aaaaaaaa-0000-0000-0000-000000000004', 2, 3, 5, 3, 'dddddddd-0000-0000-0000-000000000002', '33333333-3333-3333-3333-333333333333', digest('session-token-0004', 'sha256'), 1, 'completed', NOW() - INTERVAL '18 hours 10 minutes', NOW() - INTERVAL '18 hours', NOW() - INTERVAL '18 hours' + INTERVAL '7 days', NOW() - INTERVAL '18 hours');

-- =========================================
-- SUBMISSION EVENTS
-- =========================================

INSERT INTO submission_events (id, session_id, survey_version_id, event_type, field_uuid, received_at) VALUES
    (gen_random_uuid(), 'aaaaaaaa-0000-0000-0000-000000000001', 2, 'session_started', NULL, NOW() - INTERVAL '4 days 15 minutes'),
    (gen_random_uuid(), 'aaaaaaaa-0000-0000-0000-000000000001', 2, 'answer_saved', '00000000-0000-0000-0000-000000000003', NOW() - INTERVAL '4 days 10 minutes'),
    (gen_random_uuid(), 'aaaaaaaa-0000-0000-0000-000000000001', 2, 'session_completed', NULL, NOW() - INTERVAL '4 days'),
    (gen_random_uuid(), 'aaaaaaaa-0000-0000-0000-000000000002', 2, 'session_started', NULL, NOW() - INTERVAL '3 days 20 minutes'),
    (gen_random_uuid(), 'aaaaaaaa-0000-0000-0000-000000000002', 2, 'answer_saved', '00000000-0000-0000-0000-000000000003', NOW() - INTERVAL '3 days 10 minutes'),
    (gen_random_uuid(), 'aaaaaaaa-0000-0000-0000-000000000002', 2, 'session_completed', NULL, NOW() - INTERVAL '3 days'),
    (gen_random_uuid(), 'aaaaaaaa-0000-0000-0000-000000000003', 5, 'session_started', NULL, NOW() - INTERVAL '2 days 40 minutes'),
    (gen_random_uuid(), 'aaaaaaaa-0000-0000-0000-000000000003', 5, 'field_viewed', '00000000-0000-0000-0000-000000000011', NOW() - INTERVAL '2 days 39 minutes'),
    (gen_random_uuid(), 'aaaaaaaa-0000-0000-0000-000000000004', 5, 'session_started', NULL, NOW() - INTERVAL '18 hours 10 minutes'),
    (gen_random_uuid(), 'aaaaaaaa-0000-0000-0000-000000000004', 5, 'answer_saved', '00000000-0000-0000-0000-000000000011', NOW() - INTERVAL '18 hours 5 minutes'),
    (gen_random_uuid(), 'aaaaaaaa-0000-0000-0000-000000000004', 5, 'session_completed', NULL, NOW() - INTERVAL '18 hours');

-- =========================================
-- SUBJECT IP OBSERVATIONS
-- =========================================
-- When both subject and session are populated, the subject must match the
-- subject attached to that session (enforced by composite FK).

INSERT INTO subject_ip_observations (project_id, project_subject_id, submission_session_id, ip_address, observed_at) VALUES
    (1, '11111111-1111-1111-1111-111111111111', 'aaaaaaaa-0000-0000-0000-000000000001', '203.0.113.10', NOW() - INTERVAL '4 days 15 minutes'),
    (1, '66666666-6666-6666-6666-666666666666', 'aaaaaaaa-0000-0000-0000-000000000002', '203.0.113.22', NOW() - INTERVAL '3 days 20 minutes'),
    (2, NULL, 'aaaaaaaa-0000-0000-0000-000000000003', '198.51.100.7', NOW() - INTERVAL '2 days 40 minutes'),
    (1, '11111111-1111-1111-1111-111111111111', NULL, '203.0.113.11', NOW() - INTERVAL '20 days');

-- =========================================
-- AUDIT LOGS
-- =========================================

INSERT INTO audit_logs (id, user_id, action, entity_type, entity_id, metadata, created_at) VALUES
    (1, 2, 'project.created', 'project', 1, $json${"slug":"acme-employee-feedback"}$json$::jsonb, NOW() - INTERVAL '34 days'),
    (2, 3, 'survey.version.published', 'survey_version', 2, $json${"survey_id":1,"version_number":2}$json$::jsonb, NOW() - INTERVAL '6 days'),
    (3, 5, 'survey.version.published', 'survey_version', 5, $json${"survey_id":3,"version_number":2}$json$::jsonb, NOW() - INTERVAL '2 days');

-- =========================================
-- PUBLISH SELECTED VERSIONS
-- =========================================

UPDATE survey_versions
SET
    status = 'published',
    published_at = NOW() - INTERVAL '6 days',
    updated_at = NOW() - INTERVAL '6 days'
WHERE id = 2;

UPDATE survey_versions
SET
    status = 'published',
    published_at = NOW() - INTERVAL '2 days',
    updated_at = NOW() - INTERVAL '2 days'
WHERE id = 5;

UPDATE surveys
SET published_version_id = 2, updated_at = NOW() - INTERVAL '6 days'
WHERE id = 1;

UPDATE surveys
SET published_version_id = 5, updated_at = NOW() - INTERVAL '2 days'
WHERE id = 3;

-- =========================================
-- SEQUENCE RESET
-- =========================================

SELECT setval('users_id_seq', COALESCE((SELECT MAX(id) FROM users), 1), true);
SELECT setval('projects_id_seq', COALESCE((SELECT MAX(id) FROM projects), 1), true);
SELECT setval('permissions_id_seq', COALESCE((SELECT MAX(id) FROM permissions), 1), true);
SELECT setval('project_roles_id_seq', COALESCE((SELECT MAX(id) FROM project_roles), 1), true);
SELECT setval('project_memberships_id_seq', COALESCE((SELECT MAX(id) FROM project_memberships), 1), true);

-- =========================================
-- PROJECT INVITATIONS
-- =========================================

INSERT INTO project_invitations
    (id, project_id, invited_email, role_id, invited_by_user_id, status, token_hash, created_at) VALUES
    (1, 1, 'pending.invite@example.com', 3, 2, 'pending', encode(digest('mock-invitation-0001', 'sha256'), 'hex'),
     NOW() - INTERVAL '5 days');

SELECT setval('project_invitations_id_seq', COALESCE((SELECT MAX(id) FROM project_invitations), 1), true);
SELECT setval('response_stores_id_seq', COALESCE((SELECT MAX(id) FROM response_stores), 1), true);
SELECT setval('surveys_id_seq', COALESCE((SELECT MAX(id) FROM surveys), 1), true);
SELECT setval('survey_versions_id_seq', COALESCE((SELECT MAX(id) FROM survey_versions), 1), true);
SELECT setval('survey_roles_id_seq', COALESCE((SELECT MAX(id) FROM survey_roles), 1), true);
SELECT setval('subject_ip_observations_id_seq', COALESCE((SELECT MAX(id) FROM subject_ip_observations), 1), true);
SELECT setval('audit_logs_id_seq', COALESCE((SELECT MAX(id) FROM audit_logs), 1), true);

COMMIT;
