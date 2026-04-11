-- Active: 1774882034658@@localhost@5432@flowform_core@core_app
-- =========================================
-- FLOWFORM CORE DATABASE MOCK DATA
-- =========================================
-- Purpose:
-- - seeds realistic mock data for local development and testing
-- - keeps referential integrity intact against flowform_core_db_schema_v4.sql
--
-- Notes:
-- - uses explicit IDs so the response DB seed can line up with survey_submissions.id
-- - inserts survey version parts while versions are still draft, then publishes them
-- - question_schema / rule_schema / scoring_schema now follow the v1 JSON shape spec
-- - compiled_schema mirrors the same shapes so published artifacts resemble the stored inputs
-- - resets sequences at the end so later inserts continue cleanly
--
-- Safe to run on an empty schema.

BEGIN;

-- =========================================
-- USERS
-- =========================================

INSERT INTO users (id, auth0_user_id, email, display_name, created_at) VALUES
    (1, 'auth0|flowform-admin',   'alex@flowform.dev',   'Alex Carter',   NOW() - INTERVAL '40 days'),
    (2, 'auth0|project-owner',    'maya@acme.dev',       'Maya Singh',    NOW() - INTERVAL '35 days'),
    (3, 'auth0|project-editor',   'liam@acme.dev',       'Liam Turner',   NOW() - INTERVAL '30 days'),
    (4, 'auth0|project-viewer',   'zoe@acme.dev',        'Zoe Walker',    NOW() - INTERVAL '28 days'),
    (5, 'auth0|survey-analyst',   'noah@beta.dev',       'Noah Bennett',  NOW() - INTERVAL '24 days'),
    (6, 'auth0|public-link-user', 'guest@example.test',  'Public Guest',  NOW() - INTERVAL '10 days');

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
    -- Owner (role 1): all permissions
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
    -- Editor (role 2)
    (2, 'survey:view'),
    (2, 'survey:create'),
    (2, 'survey:edit'),
    (2, 'survey:publish'),
    (2, 'submission:view'),
    -- Viewer (role 3)
    (3, 'survey:view'),
    (3, 'submission:view'),
    -- Owner (role 4): all permissions
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
    -- Analyst (role 5)
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

INSERT INTO response_stores (
    id,
    project_id,
    name,
    store_type,
    connection_reference,
    is_active,
    created_by_user_id,
    created_at,
    updated_at
) VALUES
    (
        1,
        1,
        'Platform Primary',
        'platform_postgres',
        '{"driver":"postgres","database":"flowform_response","schema":"public"}'::jsonb,
        TRUE,
        2,
        NOW() - INTERVAL '34 days',
        NOW() - INTERVAL '2 days'
    ),
    (
        2,
        1,
        'Client Warehouse',
        'external_postgres',
        '{"secret_ref":"acme/prod/warehouse","host":"warehouse.acme.internal","database":"survey_results"}'::jsonb,
        TRUE,
        2,
        NOW() - INTERVAL '15 days',
        NOW() - INTERVAL '1 day'
    ),
    (
        3,
        2,
        'Platform Analytics',
        'platform_postgres',
        '{"driver":"postgres","database":"flowform_response_beta","schema":"public"}'::jsonb,
        TRUE,
        5,
        NOW() - INTERVAL '22 days',
        NOW() - INTERVAL '12 hours'
    );

-- =========================================
-- SURVEYS
-- =========================================

INSERT INTO surveys (
    id,
    project_id,
    title,
    visibility,
    allow_public_responses,
    public_slug,
    default_response_store_id,
    published_version_id,
    created_by_user_id,
    created_at,
    updated_at
) VALUES
    (
        1,
        1,
        'Employee Engagement Pulse',
        'link_only',
        TRUE,
        'employee-engagement-pulse',
        1,
        NULL,
        2,
        NOW() - INTERVAL '28 days',
        NOW() - INTERVAL '2 days'
    ),
    (
        2,
        1,
        'Manager Effectiveness Review',
        'private',
        FALSE,
        NULL,
        2,
        NULL,
        3,
        NOW() - INTERVAL '18 days',
        NOW() - INTERVAL '18 hours'
    ),
    (
        3,
        2,
        'Beta Signup Experience',
        'public',
        TRUE,
        'beta-signup-experience',
        3,
        NULL,
        5,
        NOW() - INTERVAL '14 days',
        NOW() - INTERVAL '6 hours'
    );

-- =========================================
-- SURVEY VERSIONS
-- =========================================
-- Insert all versions as draft first so parts can be added before publishing.

INSERT INTO survey_versions (
    id,
    survey_id,
    version_number,
    status,
    compiled_schema,
    published_at,
    created_by_user_id,
    created_at,
    updated_at,
    deleted_at
) VALUES
    (1, 1, 1, 'draft', NULL, NULL, 2, NOW() - INTERVAL '27 days', NOW() - INTERVAL '27 days', NULL),
    (2, 1, 2, 'draft', NULL, NULL, 3, NOW() - INTERVAL '7 days',  NOW() - INTERVAL '7 days',  NULL),
    (3, 2, 1, 'draft', NULL, NULL, 3, NOW() - INTERVAL '17 days', NOW() - INTERVAL '17 days', NULL),
    (4, 3, 1, 'draft', NULL, NULL, 5, NOW() - INTERVAL '13 days', NOW() - INTERVAL '13 days', NULL),
    (5, 3, 2, 'draft', NULL, NULL, 5, NOW() - INTERVAL '3 days',  NOW() - INTERVAL '3 days',  NULL);

-- =========================================
-- SURVEY QUESTIONS
-- =========================================

INSERT INTO survey_questions (id, survey_version_id, question_key, question_schema, created_at, updated_at) VALUES
    (1, 1, 'engagement_score', '{"family":"rating","label":"How engaged do you feel at work?","schema":{"min":1,"max":10},"ui":{"style":"slider"}}'::jsonb, NOW() - INTERVAL '27 days', NOW() - INTERVAL '27 days'),
    (2, 1, 'team_support', '{"family":"choice","label":"How supported do you feel by your team?","schema":{"options":[{"id":"very_supported","label":"Very supported"},{"id":"somewhat_supported","label":"Somewhat supported"},{"id":"not_supported","label":"Not supported"}],"min_selected":1,"max_selected":1},"ui":{"style":"radio"}}'::jsonb, NOW() - INTERVAL '27 days', NOW() - INTERVAL '27 days'),
    (3, 2, 'engagement_score', '{"family":"rating","label":"How engaged do you feel at work?","schema":{"min":1,"max":10},"ui":{"style":"slider"}}'::jsonb, NOW() - INTERVAL '7 days', NOW() - INTERVAL '7 days'),
    (4, 2, 'team_support', '{"family":"choice","label":"How supported do you feel by your team?","schema":{"options":[{"id":"very_supported","label":"Very supported"},{"id":"somewhat_supported","label":"Somewhat supported"},{"id":"not_supported","label":"Not supported"}],"min_selected":1,"max_selected":1},"ui":{"style":"radio"}}'::jsonb, NOW() - INTERVAL '7 days', NOW() - INTERVAL '7 days'),
    (5, 2, 'manager_feedback', '{"family":"field","label":"What is one thing your manager could do better?","schema":{"field_type":"text"},"ui":{"style":"textarea","placeholder":"Share one practical improvement"}}'::jsonb, NOW() - INTERVAL '7 days', NOW() - INTERVAL '7 days'),
    (6, 3, 'clarity_rating', '{"family":"rating","label":"My manager sets clear expectations","schema":{"min":1,"max":5},"ui":{"style":"slider"}}'::jsonb, NOW() - INTERVAL '17 days', NOW() - INTERVAL '17 days'),
    (7, 3, 'coaching_examples', '{"family":"field","label":"Share an example of good coaching","schema":{"field_type":"text"},"ui":{"style":"textarea","placeholder":"Describe a specific example"}}'::jsonb, NOW() - INTERVAL '17 days', NOW() - INTERVAL '17 days'),
    (8, 4, 'signup_ease', '{"family":"rating","label":"How easy was signup?","schema":{"min":1,"max":10},"ui":{"style":"slider"}}'::jsonb, NOW() - INTERVAL '13 days', NOW() - INTERVAL '13 days'),
    (9, 4, 'feature_interest', '{"family":"matching","label":"Match each persona to the feature they cared about most","schema":{"left_items":[{"id":"founder","label":"Founder"},{"id":"marketer","label":"Marketer"}],"right_items":[{"id":"automation","label":"Automation"},{"id":"analytics","label":"Analytics"}]},"ui":{"style":"drag_match"}}'::jsonb, NOW() - INTERVAL '13 days', NOW() - INTERVAL '13 days'),
    (10, 5, 'signup_ease', '{"family":"rating","label":"How easy was signup?","schema":{"min":1,"max":10},"ui":{"style":"slider"}}'::jsonb, NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days'),
    (11, 5, 'feature_interest', '{"family":"matching","label":"Match each persona to the feature they cared about most","schema":{"left_items":[{"id":"founder","label":"Founder"},{"id":"marketer","label":"Marketer"}],"right_items":[{"id":"automation","label":"Automation"},{"id":"analytics","label":"Analytics"}]},"ui":{"style":"drag_match"}}'::jsonb, NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days'),
    (12, 5, 'followup_email', '{"family":"field","label":"Leave your email if you want follow-up","schema":{"field_type":"email"},"ui":{"placeholder":"name@example.com"}}'::jsonb, NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days');

-- =========================================
-- SURVEY RULES
-- =========================================

INSERT INTO survey_rules (id, survey_version_id, rule_key, rule_schema, created_at, updated_at) VALUES
    (
        1,
        2,
        'show_manager_feedback_low_score',
        '{"target":"manager_feedback","sort_order":20,"condition":{"fact":"answers.engagement_score","operator":"lte","value":6},"effects":{"visible":true,"required":true}}'::jsonb,
        NOW() - INTERVAL '7 days',
        NOW() - INTERVAL '7 days'
    ),
    (
        2,
        5,
        'show_followup_email_high_ease',
        '{"target":"followup_email","sort_order":20,"condition":{"fact":"answers.signup_ease","operator":"gte","value":8},"effects":{"visible":true,"required":false}}'::jsonb,
        NOW() - INTERVAL '3 days',
        NOW() - INTERVAL '3 days'
    );

-- =========================================
-- SURVEY SCORING RULES
-- =========================================

INSERT INTO survey_scoring_rules (id, survey_version_id, scoring_key, scoring_schema, created_at, updated_at) VALUES
    (
        1,
        2,
        'engagement_score_direct',
        '{"target":"engagement_score","bucket":"engagement","strategy":"rating_direct","config":{"multiplier":1}}'::jsonb,
        NOW() - INTERVAL '7 days',
        NOW() - INTERVAL '7 days'
    ),
    (
        2,
        2,
        'team_support_option_map',
        '{"target":"team_support","bucket":"engagement","strategy":"choice_option_map","config":{"option_scores":{"very_supported":10,"somewhat_supported":6,"not_supported":2},"combine":"max"}}'::jsonb,
        NOW() - INTERVAL '7 days',
        NOW() - INTERVAL '7 days'
    ),
    (
        3,
        5,
        'signup_ease_direct',
        '{"target":"signup_ease","bucket":"total","strategy":"rating_direct","config":{"multiplier":1}}'::jsonb,
        NOW() - INTERVAL '3 days',
        NOW() - INTERVAL '3 days'
    ),
    (
        4,
        5,
        'feature_interest_answer_key',
        '{"target":"feature_interest","bucket":"total","strategy":"matching_answer_key","config":{"correct_pairs":[{"left_id":"founder","right_id":"automation"},{"left_id":"marketer","right_id":"analytics"}],"points_per_correct":1,"penalty_per_incorrect":0,"max_score":2}}'::jsonb,
        NOW() - INTERVAL '3 days',
        NOW() - INTERVAL '3 days'
    );

-- =========================================
-- SURVEY ROLES
-- =========================================

INSERT INTO survey_roles (id, project_id, name, created_at) VALUES
    (1, 1, 'Survey Admin', NOW() - INTERVAL '28 days'),
    (2, 1, 'Survey Reviewer', NOW() - INTERVAL '28 days'),
    (3, 2, 'Research Lead', NOW() - INTERVAL '13 days');

INSERT INTO survey_role_permissions (role_id, permission_id)
SELECT r.role_id, p.id
FROM (VALUES
    -- Survey Admin (role 1)
    (1, 'survey:edit'),
    (1, 'survey:delete'),
    (1, 'survey:publish'),
    (1, 'survey:archive'),
    (1, 'submission:view'),
    -- Survey Reviewer (role 2)
    (2, 'survey:view'),
    (2, 'submission:view'),
    -- Research Lead (role 3)
    (3, 'survey:view'),
    (3, 'survey:edit'),
    (3, 'survey:publish'),
    (3, 'submission:view')
) AS r(role_id, perm_name)
JOIN permissions p ON p.name = r.perm_name;

INSERT INTO survey_membership_roles (project_id, survey_id, membership_id, role_id, created_at) VALUES
    (1, 1, 1, 1, NOW() - INTERVAL '26 days'),
    (1, 1, 2, 2, NOW() - INTERVAL '6 days'),
    (2, 3, 4, 3, NOW() - INTERVAL '12 days');

-- =========================================
-- PUBLIC LINKS
-- =========================================

INSERT INTO survey_public_links (
    id,
    survey_id,
    token_prefix,
    token_hash,
    is_active,
    allow_response,
    expires_at,
    created_at
) VALUES
    (
        1,
        1,
        'acmepuls01',
        repeat('a', 64),
        TRUE,
        TRUE,
        NOW() + INTERVAL '30 days',
        NOW() - INTERVAL '5 days'
    ),
    (
        2,
        3,
        'betasign02',
        repeat('b', 64),
        TRUE,
        TRUE,
        NOW() + INTERVAL '14 days',
        NOW() - INTERVAL '2 days'
    );

-- =========================================
-- RESPONSE SUBJECT MAPPINGS
-- =========================================

INSERT INTO response_subject_mappings (
    id,
    project_id,
    user_id,
    pseudonymous_subject_id,
    created_at
) VALUES
    (1, 1, 2, '11111111-1111-1111-1111-111111111111', NOW() - INTERVAL '25 days'),
    (2, 1, 3, '22222222-2222-2222-2222-222222222222', NOW() - INTERVAL '25 days'),
    (3, 2, 5, '33333333-3333-3333-3333-333333333333', NOW() - INTERVAL '11 days');

-- =========================================
-- SURVEY SUBMISSIONS
-- =========================================

INSERT INTO survey_submissions (
    id,
    project_id,
    survey_id,
    survey_version_id,
    response_store_id,
    submission_channel,
    submitted_by_user_id,
    public_link_id,
    pseudonymous_subject_id,
    external_submission_id,
    status,
    is_anonymous,
    started_at,
    submitted_at,
    last_delivery_attempt_at,
    delivery_error,
    created_at
) VALUES
    (
        1,
        1,
        1,
        2,
        1,
        'authenticated',
        2,
        NULL,
        '11111111-1111-1111-1111-111111111111',
        'core-sub-0001',
        'stored',
        FALSE,
        NOW() - INTERVAL '4 days 15 minutes',
        NOW() - INTERVAL '4 days',
        NOW() - INTERVAL '4 days',
        NULL,
        NOW() - INTERVAL '4 days 16 minutes'
    ),
    (
        2,
        1,
        1,
        2,
        1,
        'public_link',
        NULL,
        1,
        NULL,
        'core-sub-0002',
        'stored',
        TRUE,
        NOW() - INTERVAL '3 days 20 minutes',
        NOW() - INTERVAL '3 days',
        NOW() - INTERVAL '3 days',
        NULL,
        NOW() - INTERVAL '3 days 25 minutes'
    ),
    (
        3,
        2,
        3,
        5,
        3,
        'system',
        NULL,
        NULL,
        NULL,
        'core-sub-0003',
        'failed',
        TRUE,
        NOW() - INTERVAL '2 days 40 minutes',
        NOW() - INTERVAL '2 days',
        NOW() - INTERVAL '2 days',
        'Write timeout while storing submission payload',
        NOW() - INTERVAL '2 days 45 minutes'
    ),
    (
        4,
        2,
        3,
        5,
        3,
        'public_link',
        NULL,
        2,
        NULL,
        'core-sub-0004',
        'stored',
        TRUE,
        NOW() - INTERVAL '18 hours 10 minutes',
        NOW() - INTERVAL '18 hours',
        NOW() - INTERVAL '18 hours',
        NULL,
        NOW() - INTERVAL '18 hours 15 minutes'
    );

-- =========================================
-- AUDIT LOGS
-- =========================================

INSERT INTO audit_logs (id, user_id, action, entity_type, entity_id, metadata, created_at) VALUES
    (
        1,
        2,
        'project.created',
        'project',
        1,
        '{"slug":"acme-employee-feedback"}'::jsonb,
        NOW() - INTERVAL '34 days'
    ),
    (
        2,
        3,
        'survey.version.published',
        'survey_version',
        2,
        '{"survey_id":1,"version_number":2}'::jsonb,
        NOW() - INTERVAL '6 days'
    ),
    (
        3,
        5,
        'survey.version.published',
        'survey_version',
        5,
        '{"survey_id":3,"version_number":2}'::jsonb,
        NOW() - INTERVAL '2 days'
    ),
    (
        4,
        NULL,
        'submission.delivery_failed',
        'survey_submission',
        3,
        '{"response_store_id":3,"reason":"timeout"}'::jsonb,
        NOW() - INTERVAL '2 days'
    );

-- =========================================
-- PUBLISH SELECTED VERSIONS
-- =========================================

UPDATE survey_versions
SET
    status = 'published',
    compiled_schema = '{"questions":[{"question_key":"engagement_score","question_schema":{"family":"rating","label":"How engaged do you feel at work?","schema":{"min":1,"max":10},"ui":{"style":"slider"}}},{"question_key":"team_support","question_schema":{"family":"choice","label":"How supported do you feel by your team?","schema":{"options":[{"id":"very_supported","label":"Very supported"},{"id":"somewhat_supported","label":"Somewhat supported"},{"id":"not_supported","label":"Not supported"}],"min_selected":1,"max_selected":1},"ui":{"style":"radio"}}},{"question_key":"manager_feedback","question_schema":{"family":"field","label":"What is one thing your manager could do better?","schema":{"field_type":"text"},"ui":{"style":"textarea","placeholder":"Share one practical improvement"}}}],"rules":[{"rule_key":"show_manager_feedback_low_score","rule_schema":{"target":"manager_feedback","sort_order":20,"condition":{"fact":"answers.engagement_score","operator":"lte","value":6},"effects":{"visible":true,"required":true}}}],"scoring":[{"scoring_key":"engagement_score_direct","scoring_schema":{"target":"engagement_score","bucket":"engagement","strategy":"rating_direct","config":{"multiplier":1}}},{"scoring_key":"team_support_option_map","scoring_schema":{"target":"team_support","bucket":"engagement","strategy":"choice_option_map","config":{"option_scores":{"very_supported":10,"somewhat_supported":6,"not_supported":2},"combine":"max"}}}]}'::jsonb,
    published_at = NOW() - INTERVAL '6 days',
    updated_at = NOW() - INTERVAL '6 days'
WHERE id = 2;

UPDATE survey_versions
SET
    status = 'published',
    compiled_schema = '{"questions":[{"question_key":"signup_ease","question_schema":{"family":"rating","label":"How easy was signup?","schema":{"min":1,"max":10},"ui":{"style":"slider"}}},{"question_key":"feature_interest","question_schema":{"family":"matching","label":"Match each persona to the feature they cared about most","schema":{"left_items":[{"id":"founder","label":"Founder"},{"id":"marketer","label":"Marketer"}],"right_items":[{"id":"automation","label":"Automation"},{"id":"analytics","label":"Analytics"}]},"ui":{"style":"drag_match"}}},{"question_key":"followup_email","question_schema":{"family":"field","label":"Leave your email if you want follow-up","schema":{"field_type":"email"},"ui":{"placeholder":"name@example.com"}}}],"rules":[{"rule_key":"show_followup_email_high_ease","rule_schema":{"target":"followup_email","sort_order":20,"condition":{"fact":"answers.signup_ease","operator":"gte","value":8},"effects":{"visible":true,"required":false}}}],"scoring":[{"scoring_key":"signup_ease_direct","scoring_schema":{"target":"signup_ease","bucket":"total","strategy":"rating_direct","config":{"multiplier":1}}},{"scoring_key":"feature_interest_answer_key","scoring_schema":{"target":"feature_interest","bucket":"total","strategy":"matching_answer_key","config":{"correct_pairs":[{"left_id":"founder","right_id":"automation"},{"left_id":"marketer","right_id":"analytics"}],"points_per_correct":1,"penalty_per_incorrect":0,"max_score":2}}}]}'::jsonb,
    published_at = NOW() - INTERVAL '2 days',
    updated_at = NOW() - INTERVAL '2 days'
WHERE id = 5;

UPDATE surveys
SET
    published_version_id = 2,
    updated_at = NOW() - INTERVAL '6 days'
WHERE id = 1;

UPDATE surveys
SET
    published_version_id = 5,
    updated_at = NOW() - INTERVAL '2 days'
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
SELECT setval('survey_rules_id_seq', COALESCE((SELECT MAX(id) FROM survey_rules), 1), true);
SELECT setval('survey_scoring_rules_id_seq', COALESCE((SELECT MAX(id) FROM survey_scoring_rules), 1), true);
SELECT setval('survey_roles_id_seq', COALESCE((SELECT MAX(id) FROM survey_roles), 1), true);
SELECT setval('survey_public_links_id_seq', COALESCE((SELECT MAX(id) FROM survey_public_links), 1), true);
SELECT setval('response_subject_mappings_id_seq', COALESCE((SELECT MAX(id) FROM response_subject_mappings), 1), true);
SELECT setval('survey_submissions_id_seq', COALESCE((SELECT MAX(id) FROM survey_submissions), 1), true);
SELECT setval('audit_logs_id_seq', COALESCE((SELECT MAX(id) FROM audit_logs), 1), true);

COMMIT;
