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
-- Notes:
-- - survey_questions now stores both question and rule nodes, with a UUID id
-- - sort_key and node_type are first-class columns
-- - question_schema follows the current { type, content } node shape
-- - compiled_schema mirrors the same node shape used by survey_questions
-- - project_subjects/submission_sessions/submission_events replace the old
--   response_subject_mappings/survey_submissions tables
--
-- Safe to run on an empty schema.

BEGIN;

-- =========================================
-- USERS
-- =========================================

INSERT INTO users (id, public_id, auth0_user_id, email, display_name, created_at, platform_admin) VALUES
    (1, 'A1x9Kq43', 'auth0|flowform-admin',   'alex@flowform.dev',   'Alex Carter',   NOW() - INTERVAL '40 days', TRUE),
    (2, 'M7s2Qa23', 'auth0|project-owner',    'maya@acme.dev',       'Maya Singh',    NOW() - INTERVAL '35 days', FALSE),
    (3, 'L4t8Np34', 'auth0|project-editor',   'liam@acme.dev',       'Liam Turner',   NOW() - INTERVAL '30 days', FALSE),
    (4, 'Z9w3Vr64', 'auth0|project-viewer',   'zoe@acme.dev',        'Zoe Walker',    NOW() - INTERVAL '28 days', FALSE),
    (5, 'N2b6Hx25', 'auth0|research-owner',   'noah@beta.dev',       'Noah Bennett',  NOW() - INTERVAL '24 days', FALSE),
    (6, 'G5p1Yu15', 'auth0|public-link-user', 'guest@example.test',  'Public Guest',  NOW() - INTERVAL '10 days', FALSE);

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
-- Insert all versions as draft first so nodes can be added before publishing.

INSERT INTO survey_versions (id, survey_id, version_number, status, compiled_schema, published_at, created_by_user_id, created_at, updated_at, deleted_at) VALUES
    (1, 1, 1, 'draft', NULL, NULL, 2, NOW() - INTERVAL '27 days', NOW() - INTERVAL '27 days', NULL),
    (2, 1, 2, 'draft', NULL, NULL, 3, NOW() - INTERVAL '7 days',  NOW() - INTERVAL '7 days',  NULL),
    (3, 2, 1, 'draft', NULL, NULL, 3, NOW() - INTERVAL '17 days', NOW() - INTERVAL '17 days', NULL),
    (4, 3, 1, 'draft', NULL, NULL, 5, NOW() - INTERVAL '13 days', NOW() - INTERVAL '13 days', NULL),
    (5, 3, 2, 'draft', NULL, NULL, 5, NOW() - INTERVAL '3 days',  NOW() - INTERVAL '3 days',  NULL);

-- =========================================
-- SURVEY QUESTIONS / NODES
-- =========================================

INSERT INTO survey_questions (id, survey_version_id, question_key, sort_key, node_type, question_schema, created_at, updated_at) VALUES
    ('00000000-0000-0000-0000-000000000001', 1, 'engagement_score', 100000, 'question', $json${"type":"question","content":{"id":"engagement_score","title":"Engagement Score","label":"How engaged do you feel at work?","family":"rating","definition":{"variant":"slider","range":{"min":1,"max":10,"step":1},"ui":{"left_label":"Not engaged","right_label":"Very engaged"}}}}$json$::jsonb, NOW() - INTERVAL '27 days', NOW() - INTERVAL '27 days'),
    ('00000000-0000-0000-0000-000000000002', 1, 'team_support', 200000, 'question', $json${"type":"question","content":{"id":"team_support","title":"Team Support","label":"How supported do you feel by your team?","family":"choice","definition":{"min":1,"max":1,"options":[{"id":"very_supported","label":"Very supported"},{"id":"somewhat_supported","label":"Somewhat supported"},{"id":"not_supported","label":"Not supported"}]}}}$json$::jsonb, NOW() - INTERVAL '27 days', NOW() - INTERVAL '27 days'),
    ('00000000-0000-0000-0000-000000000003', 2, 'engagement_score', 100000, 'question', $json${"type":"question","content":{"id":"engagement_score","title":"Engagement Score","label":"How engaged do you feel at work?","family":"rating","definition":{"variant":"slider","range":{"min":1,"max":10,"step":1},"ui":{"left_label":"Not engaged","right_label":"Very engaged"}}}}$json$::jsonb, NOW() - INTERVAL '7 days', NOW() - INTERVAL '7 days'),
    ('00000000-0000-0000-0000-000000000004', 2, 'team_support', 200000, 'question', $json${"type":"question","content":{"id":"team_support","title":"Team Support","label":"How supported do you feel by your team?","family":"choice","definition":{"min":1,"max":1,"options":[{"id":"very_supported","label":"Very supported"},{"id":"somewhat_supported","label":"Somewhat supported"},{"id":"not_supported","label":"Not supported"}]}}}$json$::jsonb, NOW() - INTERVAL '7 days', NOW() - INTERVAL '7 days'),
    ('00000000-0000-0000-0000-000000000005', 2, 'manager_feedback', 300000, 'question', $json${"type":"question","content":{"id":"manager_feedback","title":"Manager Feedback","label":"What is one thing your manager could do better?","family":"field","definition":{"variant":"textarea","field_type":"text","placeholder":"Share one practical improvement"}}}$json$::jsonb, NOW() - INTERVAL '7 days', NOW() - INTERVAL '7 days'),
    ('00000000-0000-0000-0000-000000000006', 2, 'show_manager_feedback_low_score', 400000, 'rule', $json${"type":"rule","content":{"id":"show_manager_feedback_low_score","title":"Show manager feedback for low scores","target":"manager_feedback","condition":{"question_key":"engagement_score","operator":"lte","value":6},"effects":{"visible":true,"required":true}}}$json$::jsonb, NOW() - INTERVAL '7 days', NOW() - INTERVAL '7 days'),
    ('00000000-0000-0000-0000-000000000007', 3, 'clarity_rating', 100000, 'question', $json${"type":"question","content":{"id":"clarity_rating","title":"Clear Expectations","label":"My manager sets clear expectations.","family":"rating","definition":{"variant":"slider","range":{"min":1,"max":5,"step":1},"ui":{"left_label":"Strongly disagree","right_label":"Strongly agree"}}}}$json$::jsonb, NOW() - INTERVAL '17 days', NOW() - INTERVAL '17 days'),
    ('00000000-0000-0000-0000-000000000008', 3, 'coaching_examples', 200000, 'question', $json${"type":"question","content":{"id":"coaching_examples","title":"Coaching Example","label":"Share an example of good coaching.","family":"field","definition":{"variant":"textarea","field_type":"text","placeholder":"Describe a specific example"}}}$json$::jsonb, NOW() - INTERVAL '17 days', NOW() - INTERVAL '17 days'),
    ('00000000-0000-0000-0000-000000000009', 4, 'signup_ease', 100000, 'question', $json${"type":"question","content":{"id":"signup_ease","title":"Signup Ease","label":"How easy was signup?","family":"rating","definition":{"variant":"slider","range":{"min":1,"max":10,"step":1},"ui":{"left_label":"Difficult","right_label":"Easy"}}}}$json$::jsonb, NOW() - INTERVAL '13 days', NOW() - INTERVAL '13 days'),
    ('00000000-0000-0000-0000-000000000010', 4, 'feature_interest', 200000, 'question', $json${"type":"question","content":{"id":"feature_interest","title":"Feature Interest","label":"Match each persona to the feature they cared about most.","family":"matching","definition":{"left_items":[{"id":"founder","label":"Founder"},{"id":"marketer","label":"Marketer"}],"right_items":[{"id":"automation","label":"Automation"},{"id":"analytics","label":"Analytics"}]}}}$json$::jsonb, NOW() - INTERVAL '13 days', NOW() - INTERVAL '13 days'),
    ('00000000-0000-0000-0000-000000000011', 5, 'signup_ease', 100000, 'question', $json${"type":"question","content":{"id":"signup_ease","title":"Signup Ease","label":"How easy was signup?","family":"rating","definition":{"variant":"slider","range":{"min":1,"max":10,"step":1},"ui":{"left_label":"Difficult","right_label":"Easy"}}}}$json$::jsonb, NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days'),
    ('00000000-0000-0000-0000-000000000012', 5, 'feature_interest', 200000, 'question', $json${"type":"question","content":{"id":"feature_interest","title":"Feature Interest","label":"Match each persona to the feature they cared about most.","family":"matching","definition":{"left_items":[{"id":"founder","label":"Founder"},{"id":"marketer","label":"Marketer"}],"right_items":[{"id":"automation","label":"Automation"},{"id":"analytics","label":"Analytics"}]}}}$json$::jsonb, NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days'),
    ('00000000-0000-0000-0000-000000000013', 5, 'followup_email', 300000, 'question', $json${"type":"question","content":{"id":"followup_email","title":"Follow-up Email","label":"Leave your email if you want follow-up.","family":"field","definition":{"variant":"input","field_type":"email","placeholder":"name@example.com"}}}$json$::jsonb, NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days'),
    ('00000000-0000-0000-0000-000000000014', 5, 'show_followup_email_high_ease', 400000, 'rule', $json${"type":"rule","content":{"id":"show_followup_email_high_ease","title":"Show follow-up email for high ease","target":"followup_email","condition":{"question_key":"signup_ease","operator":"gte","value":8},"effects":{"visible":true,"required":false}}}$json$::jsonb, NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days');

-- =========================================
-- SURVEY SCORING RULES
-- =========================================

INSERT INTO survey_scoring_rules (id, survey_version_id, scoring_key, scoring_schema, created_at, updated_at) VALUES
    (1, 2, 'engagement_score_direct', $json${"target":"engagement_score","bucket":"engagement","strategy":"rating_direct","config":{"multiplier":1}}$json$::jsonb, NOW() - INTERVAL '7 days', NOW() - INTERVAL '7 days'),
    (2, 2, 'team_support_option_map', $json${"target":"team_support","bucket":"engagement","strategy":"choice_option_map","config":{"option_scores":{"very_supported":10,"somewhat_supported":6,"not_supported":2},"combine":"max"}}$json$::jsonb, NOW() - INTERVAL '7 days', NOW() - INTERVAL '7 days'),
    (3, 5, 'signup_ease_direct', $json${"target":"signup_ease","bucket":"total","strategy":"rating_direct","config":{"multiplier":1}}$json$::jsonb, NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days'),
    (4, 5, 'feature_interest_answer_key', $json${"target":"feature_interest","bucket":"total","strategy":"matching_answer_key","config":{"correct_pairs":[{"left_id":"founder","right_id":"automation"},{"left_id":"marketer","right_id":"analytics"}],"points_per_correct":1,"penalty_per_incorrect":0,"max_score":2}}$json$::jsonb, NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days');

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
    ('a1a1a1a1-0000-0000-0000-000000000001', 1, '11111111-1111-1111-1111-111111111111', 'authenticated_user', 2, NULL, 'verified', NOW() - INTERVAL '25 days', NOW() - INTERVAL '25 days'),
    ('a1a1a1a1-0000-0000-0000-000000000002', 1, '22222222-2222-2222-2222-222222222222', 'authenticated_user', 3, NULL, 'verified', NOW() - INTERVAL '25 days', NOW() - INTERVAL '25 days'),
    ('a1a1a1a1-0000-0000-0000-000000000003', 2, '33333333-3333-3333-3333-333333333333', 'authenticated_user', 5, NULL, 'verified', NOW() - INTERVAL '11 days', NOW() - INTERVAL '11 days'),
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
-- PUBLIC LINKS
-- =========================================
-- project_id is stored directly so the database can prove link, survey, and
-- assigned subject share a project. Email-assigned links must require auth.

INSERT INTO survey_links (id, project_id, survey_id, token_prefix, token_hash, is_active, requires_auth, assigned_email, assigned_subject_id, expires_at, created_at) VALUES
    (1, 1, 1, 'acmepuls01', repeat('a', 64), TRUE, TRUE, 'guest@example.test', NULL, NOW() + INTERVAL '30 days', NOW() - INTERVAL '5 days'),
    (2, 2, 3, 'betasign02', repeat('b', 64), TRUE, TRUE, 'noah@beta.dev', NULL, NOW() + INTERVAL '14 days', NOW() - INTERVAL '2 days');

-- =========================================
-- SUBMISSION SESSIONS
-- =========================================

INSERT INTO submission_sessions (id, project_id, survey_id, survey_version_id, response_store_id, link_id, project_subject_id, browser_session_token_hash, linkage_key_version, session_status, started_at, completed_at, expires_at, last_activity_at) VALUES
    ('aaaaaaaa-0000-0000-0000-000000000001', 1, 1, 2, 1, NULL, '11111111-1111-1111-1111-111111111111', digest('session-token-0001', 'sha256'), 1, 'completed', NOW() - INTERVAL '4 days 15 minutes', NOW() - INTERVAL '4 days', NOW() - INTERVAL '4 days' + INTERVAL '7 days', NOW() - INTERVAL '4 days'),
    ('aaaaaaaa-0000-0000-0000-000000000002', 1, 1, 2, 1, 1, '66666666-6666-6666-6666-666666666666', digest('session-token-0002', 'sha256'), 1, 'completed', NOW() - INTERVAL '3 days 20 minutes', NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days' + INTERVAL '7 days', NOW() - INTERVAL '3 days'),
    ('aaaaaaaa-0000-0000-0000-000000000003', 2, 3, 5, 3, NULL, NULL, digest('session-token-0003', 'sha256'), 1, 'abandoned', NOW() - INTERVAL '2 days 40 minutes', NULL, NOW() - INTERVAL '2 days 40 minutes' + INTERVAL '7 days', NOW() - INTERVAL '2 days 40 minutes'),
    ('aaaaaaaa-0000-0000-0000-000000000004', 2, 3, 5, 3, 2, '33333333-3333-3333-3333-333333333333', digest('session-token-0004', 'sha256'), 1, 'completed', NOW() - INTERVAL '18 hours 10 minutes', NOW() - INTERVAL '18 hours', NOW() - INTERVAL '18 hours' + INTERVAL '7 days', NOW() - INTERVAL '18 hours');

-- =========================================
-- SUBMISSION EVENTS
-- =========================================

INSERT INTO submission_events (id, session_id, survey_version_id, event_type, question_node_id, received_at) VALUES
    (gen_random_uuid(), 'aaaaaaaa-0000-0000-0000-000000000001', 2, 'session_started', NULL, NOW() - INTERVAL '4 days 15 minutes'),
    (gen_random_uuid(), 'aaaaaaaa-0000-0000-0000-000000000001', 2, 'answer_saved', '00000000-0000-0000-0000-000000000003', NOW() - INTERVAL '4 days 10 minutes'),
    (gen_random_uuid(), 'aaaaaaaa-0000-0000-0000-000000000001', 2, 'session_completed', NULL, NOW() - INTERVAL '4 days'),
    (gen_random_uuid(), 'aaaaaaaa-0000-0000-0000-000000000002', 2, 'session_started', NULL, NOW() - INTERVAL '3 days 20 minutes'),
    (gen_random_uuid(), 'aaaaaaaa-0000-0000-0000-000000000002', 2, 'answer_saved', '00000000-0000-0000-0000-000000000003', NOW() - INTERVAL '3 days 10 minutes'),
    (gen_random_uuid(), 'aaaaaaaa-0000-0000-0000-000000000002', 2, 'session_completed', NULL, NOW() - INTERVAL '3 days'),
    (gen_random_uuid(), 'aaaaaaaa-0000-0000-0000-000000000003', 5, 'session_started', NULL, NOW() - INTERVAL '2 days 40 minutes'),
    (gen_random_uuid(), 'aaaaaaaa-0000-0000-0000-000000000003', 5, 'question_viewed', '00000000-0000-0000-0000-000000000011', NOW() - INTERVAL '2 days 39 minutes'),
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
    compiled_schema = $json${"schema_version":1,"nodes":[{"sort_key":100000,"node_type":"question","question_key":"engagement_score","question_schema":{"type":"question","content":{"id":"engagement_score","title":"Engagement Score","label":"How engaged do you feel at work?","family":"rating","definition":{"variant":"slider","range":{"min":1,"max":10,"step":1},"ui":{"left_label":"Not engaged","right_label":"Very engaged"}}}}},{"sort_key":200000,"node_type":"question","question_key":"team_support","question_schema":{"type":"question","content":{"id":"team_support","title":"Team Support","label":"How supported do you feel by your team?","family":"choice","definition":{"min":1,"max":1,"options":[{"id":"very_supported","label":"Very supported"},{"id":"somewhat_supported","label":"Somewhat supported"},{"id":"not_supported","label":"Not supported"}]}}}},{"sort_key":300000,"node_type":"question","question_key":"manager_feedback","question_schema":{"type":"question","content":{"id":"manager_feedback","title":"Manager Feedback","label":"What is one thing your manager could do better?","family":"field","definition":{"variant":"textarea","field_type":"text","placeholder":"Share one practical improvement"}}}},{"sort_key":400000,"node_type":"rule","question_key":"show_manager_feedback_low_score","question_schema":{"type":"rule","content":{"id":"show_manager_feedback_low_score","title":"Show manager feedback for low scores","target":"manager_feedback","condition":{"question_key":"engagement_score","operator":"lte","value":6},"effects":{"visible":true,"required":true}}}}],"scoring":[{"scoring_key":"engagement_score_direct","scoring_schema":{"target":"engagement_score","bucket":"engagement","strategy":"rating_direct","config":{"multiplier":1}}},{"scoring_key":"team_support_option_map","scoring_schema":{"target":"team_support","bucket":"engagement","strategy":"choice_option_map","config":{"option_scores":{"very_supported":10,"somewhat_supported":6,"not_supported":2},"combine":"max"}}}]}$json$::jsonb,
    published_at = NOW() - INTERVAL '6 days',
    updated_at = NOW() - INTERVAL '6 days'
WHERE id = 2;

UPDATE survey_versions
SET
    status = 'published',
    compiled_schema = $json${"schema_version":1,"nodes":[{"sort_key":100000,"node_type":"question","question_key":"signup_ease","question_schema":{"type":"question","content":{"id":"signup_ease","title":"Signup Ease","label":"How easy was signup?","family":"rating","definition":{"variant":"slider","range":{"min":1,"max":10,"step":1},"ui":{"left_label":"Difficult","right_label":"Easy"}}}}},{"sort_key":200000,"node_type":"question","question_key":"feature_interest","question_schema":{"type":"question","content":{"id":"feature_interest","title":"Feature Interest","label":"Match each persona to the feature they cared about most.","family":"matching","definition":{"left_items":[{"id":"founder","label":"Founder"},{"id":"marketer","label":"Marketer"}],"right_items":[{"id":"automation","label":"Automation"},{"id":"analytics","label":"Analytics"}]}}}},{"sort_key":300000,"node_type":"question","question_key":"followup_email","question_schema":{"type":"question","content":{"id":"followup_email","title":"Follow-up Email","label":"Leave your email if you want follow-up.","family":"field","definition":{"variant":"input","field_type":"email","placeholder":"name@example.com"}}}},{"sort_key":400000,"node_type":"rule","question_key":"show_followup_email_high_ease","question_schema":{"type":"rule","content":{"id":"show_followup_email_high_ease","title":"Show follow-up email for high ease","target":"followup_email","condition":{"question_key":"signup_ease","operator":"gte","value":8},"effects":{"visible":true,"required":false}}}}],"scoring":[{"scoring_key":"signup_ease_direct","scoring_schema":{"target":"signup_ease","bucket":"total","strategy":"rating_direct","config":{"multiplier":1}}},{"scoring_key":"feature_interest_answer_key","scoring_schema":{"target":"feature_interest","bucket":"total","strategy":"matching_answer_key","config":{"correct_pairs":[{"left_id":"founder","right_id":"automation"},{"left_id":"marketer","right_id":"analytics"}],"points_per_correct":1,"penalty_per_incorrect":0,"max_score":2}}}]}$json$::jsonb,
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

INSERT INTO project_invitations (id, project_id, invited_email, role_id, invited_by_user_id, status, created_at) VALUES
    (1, 1, 'pending.invite@example.com', 3, 2, 'pending', NOW() - INTERVAL '5 days');

SELECT setval('project_invitations_id_seq', COALESCE((SELECT MAX(id) FROM project_invitations), 1), true);
SELECT setval('response_stores_id_seq', COALESCE((SELECT MAX(id) FROM response_stores), 1), true);
SELECT setval('surveys_id_seq', COALESCE((SELECT MAX(id) FROM surveys), 1), true);
SELECT setval('survey_versions_id_seq', COALESCE((SELECT MAX(id) FROM survey_versions), 1), true);
SELECT setval('survey_scoring_rules_id_seq', COALESCE((SELECT MAX(id) FROM survey_scoring_rules), 1), true);
SELECT setval('survey_roles_id_seq', COALESCE((SELECT MAX(id) FROM survey_roles), 1), true);
SELECT setval('survey_links_id_seq', COALESCE((SELECT MAX(id) FROM survey_links), 1), true);
SELECT setval('subject_ip_observations_id_seq', COALESCE((SELECT MAX(id) FROM subject_ip_observations), 1), true);
SELECT setval('audit_logs_id_seq', COALESCE((SELECT MAX(id) FROM audit_logs), 1), true);

COMMIT;
