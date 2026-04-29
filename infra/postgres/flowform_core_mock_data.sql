-- Active: 1774882034658@@localhost@5432@flowform_core@core_app
-- =========================================
-- FLOWFORM CORE DATABASE MOCK DATA
-- =========================================
-- Purpose:
-- - seeds realistic mock data for local development and testing
-- - matches flowform_core_db_schema_v4.sql
-- - uses explicit IDs so the response DB seed can line up with survey_submissions.id
--
-- Notes:
-- - survey_questions now stores both question and rule nodes
-- - sort_key and node_type are first-class columns
-- - question_schema follows the current { type, content } node shape
-- - compiled_schema mirrors the same node shape used by survey_questions
--
-- Safe to run on an empty schema.

BEGIN;

-- =========================================
-- USERS
-- =========================================

INSERT INTO users (id, auth0_user_id, email, display_name, created_at, platform_admin) VALUES
    (1, 'auth0|flowform-admin',   'alex@flowform.dev',   'Alex Carter',   NOW() - INTERVAL '40 days', TRUE),
    (2, 'auth0|project-owner',    'maya@acme.dev',       'Maya Singh',    NOW() - INTERVAL '35 days', FALSE),
    (3, 'auth0|project-editor',   'liam@acme.dev',       'Liam Turner',   NOW() - INTERVAL '30 days', FALSE),
    (4, 'auth0|project-viewer',   'zoe@acme.dev',        'Zoe Walker',    NOW() - INTERVAL '28 days', FALSE),
    (5, 'auth0|research-owner',   'noah@beta.dev',       'Noah Bennett',  NOW() - INTERVAL '24 days', FALSE),
    (6, 'auth0|public-link-user', 'guest@example.test',  'Public Guest',  NOW() - INTERVAL '10 days', FALSE);

-- =========================================
-- PROJECTS
-- =========================================

INSERT INTO projects (id, name, slug, created_by_user_id, created_at) VALUES
    (1, 'Acme Employee Feedback', 'acme-employee-feedback', 2, NOW() - INTERVAL '34 days'),
    (2, 'Beta Product Research',  'beta-product-research',  5, NOW() - INTERVAL '22 days');

-- =========================================
-- PERMISSIONS
-- =========================================

INSERT INTO permissions (id, name) VALUES
    (1, 'project:edit'),
    (2, 'project:delete'),
    (3, 'project:manage_members'),
    (4, 'project:manage_roles'),
    (5, 'survey:view'),
    (6, 'survey:create'),
    (7, 'survey:edit'),
    (8, 'survey:delete'),
    (9, 'survey:publish'),
    (10, 'survey:archive'),
    (11, 'submission:view');

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
    (3, 4, 1, 3, 'invited', NOW() - INTERVAL '20 days'),
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
    (1, 1, 'engagement_score', 100000, 'question', $json${"type":"question","content":{"id":"engagement_score","title":"Engagement Score","label":"How engaged do you feel at work?","family":"rating","definition":{"variant":"slider","range":{"min":1,"max":10,"step":1},"ui":{"left_label":"Not engaged","right_label":"Very engaged"}}}}$json$::jsonb, NOW() - INTERVAL '27 days', NOW() - INTERVAL '27 days'),
    (2, 1, 'team_support', 200000, 'question', $json${"type":"question","content":{"id":"team_support","title":"Team Support","label":"How supported do you feel by your team?","family":"choice","definition":{"min":1,"max":1,"options":[{"id":"very_supported","label":"Very supported"},{"id":"somewhat_supported","label":"Somewhat supported"},{"id":"not_supported","label":"Not supported"}]}}}$json$::jsonb, NOW() - INTERVAL '27 days', NOW() - INTERVAL '27 days'),
    (3, 2, 'engagement_score', 100000, 'question', $json${"type":"question","content":{"id":"engagement_score","title":"Engagement Score","label":"How engaged do you feel at work?","family":"rating","definition":{"variant":"slider","range":{"min":1,"max":10,"step":1},"ui":{"left_label":"Not engaged","right_label":"Very engaged"}}}}$json$::jsonb, NOW() - INTERVAL '7 days', NOW() - INTERVAL '7 days'),
    (4, 2, 'team_support', 200000, 'question', $json${"type":"question","content":{"id":"team_support","title":"Team Support","label":"How supported do you feel by your team?","family":"choice","definition":{"min":1,"max":1,"options":[{"id":"very_supported","label":"Very supported"},{"id":"somewhat_supported","label":"Somewhat supported"},{"id":"not_supported","label":"Not supported"}]}}}$json$::jsonb, NOW() - INTERVAL '7 days', NOW() - INTERVAL '7 days'),
    (5, 2, 'manager_feedback', 300000, 'question', $json${"type":"question","content":{"id":"manager_feedback","title":"Manager Feedback","label":"What is one thing your manager could do better?","family":"field","definition":{"variant":"textarea","field_type":"text","placeholder":"Share one practical improvement"}}}$json$::jsonb, NOW() - INTERVAL '7 days', NOW() - INTERVAL '7 days'),
    (6, 2, 'show_manager_feedback_low_score', 400000, 'rule', $json${"type":"rule","content":{"id":"show_manager_feedback_low_score","title":"Show manager feedback for low scores","target":"manager_feedback","condition":{"question_key":"engagement_score","operator":"lte","value":6},"effects":{"visible":true,"required":true}}}$json$::jsonb, NOW() - INTERVAL '7 days', NOW() - INTERVAL '7 days'),
    (7, 3, 'clarity_rating', 100000, 'question', $json${"type":"question","content":{"id":"clarity_rating","title":"Clear Expectations","label":"My manager sets clear expectations.","family":"rating","definition":{"variant":"slider","range":{"min":1,"max":5,"step":1},"ui":{"left_label":"Strongly disagree","right_label":"Strongly agree"}}}}$json$::jsonb, NOW() - INTERVAL '17 days', NOW() - INTERVAL '17 days'),
    (8, 3, 'coaching_examples', 200000, 'question', $json${"type":"question","content":{"id":"coaching_examples","title":"Coaching Example","label":"Share an example of good coaching.","family":"field","definition":{"variant":"textarea","field_type":"text","placeholder":"Describe a specific example"}}}$json$::jsonb, NOW() - INTERVAL '17 days', NOW() - INTERVAL '17 days'),
    (9, 4, 'signup_ease', 100000, 'question', $json${"type":"question","content":{"id":"signup_ease","title":"Signup Ease","label":"How easy was signup?","family":"rating","definition":{"variant":"slider","range":{"min":1,"max":10,"step":1},"ui":{"left_label":"Difficult","right_label":"Easy"}}}}$json$::jsonb, NOW() - INTERVAL '13 days', NOW() - INTERVAL '13 days'),
    (10, 4, 'feature_interest', 200000, 'question', $json${"type":"question","content":{"id":"feature_interest","title":"Feature Interest","label":"Match each persona to the feature they cared about most.","family":"matching","definition":{"left_items":[{"id":"founder","label":"Founder"},{"id":"marketer","label":"Marketer"}],"right_items":[{"id":"automation","label":"Automation"},{"id":"analytics","label":"Analytics"}]}}}$json$::jsonb, NOW() - INTERVAL '13 days', NOW() - INTERVAL '13 days'),
    (11, 5, 'signup_ease', 100000, 'question', $json${"type":"question","content":{"id":"signup_ease","title":"Signup Ease","label":"How easy was signup?","family":"rating","definition":{"variant":"slider","range":{"min":1,"max":10,"step":1},"ui":{"left_label":"Difficult","right_label":"Easy"}}}}$json$::jsonb, NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days'),
    (12, 5, 'feature_interest', 200000, 'question', $json${"type":"question","content":{"id":"feature_interest","title":"Feature Interest","label":"Match each persona to the feature they cared about most.","family":"matching","definition":{"left_items":[{"id":"founder","label":"Founder"},{"id":"marketer","label":"Marketer"}],"right_items":[{"id":"automation","label":"Automation"},{"id":"analytics","label":"Analytics"}]}}}$json$::jsonb, NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days'),
    (13, 5, 'followup_email', 300000, 'question', $json${"type":"question","content":{"id":"followup_email","title":"Follow-up Email","label":"Leave your email if you want follow-up.","family":"field","definition":{"variant":"input","field_type":"email","placeholder":"name@example.com"}}}$json$::jsonb, NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days'),
    (14, 5, 'show_followup_email_high_ease', 400000, 'rule', $json${"type":"rule","content":{"id":"show_followup_email_high_ease","title":"Show follow-up email for high ease","target":"followup_email","condition":{"question_key":"signup_ease","operator":"gte","value":8},"effects":{"visible":true,"required":false}}}$json$::jsonb, NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days');

-- =========================================
-- SURVEY SCORING RULES
-- =========================================

INSERT INTO survey_scoring_rules (id, survey_version_id, scoring_key, scoring_schema, created_at, updated_at) VALUES
    (1, 2, 'engagement_score_direct', $json${"target":"engagement_score","bucket":"engagement","strategy":"rating_direct","config":{"multiplier":1}}$json$::jsonb, NOW() - INTERVAL '7 days', NOW() - INTERVAL '7 days'),
    (2, 2, 'team_support_option_map', $json${"target":"team_support","bucket":"engagement","strategy":"choice_option_map","config":{"option_scores":{"very_supported":10,"somewhat_supported":6,"not_supported":2},"combine":"max"}}$json$::jsonb, NOW() - INTERVAL '7 days', NOW() - INTERVAL '7 days'),
    (3, 5, 'signup_ease_direct', $json${"target":"signup_ease","bucket":"total","strategy":"rating_direct","config":{"multiplier":1}}$json$::jsonb, NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days'),
    (4, 5, 'feature_interest_answer_key', $json${"target":"feature_interest","bucket":"total","strategy":"matching_answer_key","config":{"correct_pairs":[{"left_id":"founder","right_id":"automation"},{"left_id":"marketer","right_id":"analytics"}],"points_per_correct":1,"penalty_per_incorrect":0,"max_score":2}}$json$::jsonb, NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days');

-- =========================================
-- PUBLIC LINKS
-- =========================================

INSERT INTO survey_links (id, survey_id, token_prefix, token_hash, is_active, assigned_email, expires_at, created_at) VALUES
    (1, 1, 'acmepuls01', repeat('a', 64), TRUE, 'guest@example.test', NOW() + INTERVAL '30 days', NOW() - INTERVAL '5 days'),
    (2, 3, 'betasign02', repeat('b', 64), TRUE, 'noah@beta.dev', NOW() + INTERVAL '14 days', NOW() - INTERVAL '2 days');

-- =========================================
-- RESPONSE SUBJECT MAPPINGS
-- =========================================

INSERT INTO response_subject_mappings (id, project_id, user_id, pseudonymous_subject_id, created_at) VALUES
    (1, 1, 2, '11111111-1111-1111-1111-111111111111', NOW() - INTERVAL '25 days'),
    (2, 1, 3, '22222222-2222-2222-2222-222222222222', NOW() - INTERVAL '25 days'),
    (3, 2, 5, '33333333-3333-3333-3333-333333333333', NOW() - INTERVAL '11 days'),
    (4, 1, 6, '66666666-6666-6666-6666-666666666666', NOW() - INTERVAL '5 days');

-- =========================================
-- SURVEY SUBMISSIONS
-- =========================================

INSERT INTO survey_submissions (id, project_id, survey_id, survey_version_id, response_store_id, submission_channel, submitted_by_user_id, survey_link_id, pseudonymous_subject_id, external_submission_id, status, is_anonymous, started_at, submitted_at, last_delivery_attempt_at, delivery_error, created_at) VALUES
    (1, 1, 1, 2, 1, 'slug', 2, NULL, '11111111-1111-1111-1111-111111111111', 'core-sub-0001', 'stored', FALSE, NOW() - INTERVAL '4 days 15 minutes', NOW() - INTERVAL '4 days', NOW() - INTERVAL '4 days', NULL, NOW() - INTERVAL '4 days 16 minutes'),
    (2, 1, 1, 2, 1, 'link', 6, 1, '66666666-6666-6666-6666-666666666666', 'core-sub-0002', 'stored', FALSE, NOW() - INTERVAL '3 days 20 minutes', NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days', NULL, NOW() - INTERVAL '3 days 25 minutes'),
    (3, 2, 3, 5, 3, 'system', NULL, NULL, NULL, 'core-sub-0003', 'failed', FALSE, NOW() - INTERVAL '2 days 40 minutes', NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days', 'Write timeout while storing submission payload', NOW() - INTERVAL '2 days 45 minutes'),
    (4, 2, 3, 5, 3, 'link', 5, 2, '33333333-3333-3333-3333-333333333333', 'core-sub-0004', 'stored', FALSE, NOW() - INTERVAL '18 hours 10 minutes', NOW() - INTERVAL '18 hours', NOW() - INTERVAL '18 hours', NULL, NOW() - INTERVAL '18 hours 15 minutes');

-- =========================================
-- AUDIT LOGS
-- =========================================

INSERT INTO audit_logs (id, user_id, action, entity_type, entity_id, metadata, created_at) VALUES
    (1, 2, 'project.created', 'project', 1, $json${"slug":"acme-employee-feedback"}$json$::jsonb, NOW() - INTERVAL '34 days'),
    (2, 3, 'survey.version.published', 'survey_version', 2, $json${"survey_id":1,"version_number":2}$json$::jsonb, NOW() - INTERVAL '6 days'),
    (3, 5, 'survey.version.published', 'survey_version', 5, $json${"survey_id":3,"version_number":2}$json$::jsonb, NOW() - INTERVAL '2 days'),
    (4, NULL, 'submission.delivery_failed', 'survey_submission', 3, $json${"response_store_id":3,"reason":"timeout"}$json$::jsonb, NOW() - INTERVAL '2 days');

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
SELECT setval('response_stores_id_seq', COALESCE((SELECT MAX(id) FROM response_stores), 1), true);
SELECT setval('surveys_id_seq', COALESCE((SELECT MAX(id) FROM surveys), 1), true);
SELECT setval('survey_versions_id_seq', COALESCE((SELECT MAX(id) FROM survey_versions), 1), true);
SELECT setval('survey_questions_id_seq', COALESCE((SELECT MAX(id) FROM survey_questions), 1), true);
SELECT setval('survey_scoring_rules_id_seq', COALESCE((SELECT MAX(id) FROM survey_scoring_rules), 1), true);
SELECT setval('survey_roles_id_seq', COALESCE((SELECT MAX(id) FROM survey_roles), 1), true);
SELECT setval('survey_links_id_seq', COALESCE((SELECT MAX(id) FROM survey_links), 1), true);
SELECT setval('response_subject_mappings_id_seq', COALESCE((SELECT MAX(id) FROM response_subject_mappings), 1), true);
SELECT setval('survey_submissions_id_seq', COALESCE((SELECT MAX(id) FROM survey_submissions), 1), true);
SELECT setval('audit_logs_id_seq', COALESCE((SELECT MAX(id) FROM audit_logs), 1), true);

COMMIT;
