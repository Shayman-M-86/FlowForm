-- Active: 1774882182463@@localhost@5433@flowform_response@response_app
-- =========================================
-- FLOWFORM RESPONSE DATABASE MOCK DATA
-- =========================================
-- Purpose:
-- - seeds realistic submission payloads for the response database
-- - matches flowform_response_db_schema_v4.sql
-- - aligns core_submission_id with survey_submissions.id from the core mock seed
--
-- Safe to run on an empty schema after running the matching core mock data.

BEGIN;

-- =========================================
-- SUBMISSIONS
-- =========================================

INSERT INTO submissions (id, core_submission_id, survey_id, survey_version_id, project_id, pseudonymous_subject_id, is_anonymous, submitted_at, metadata, created_at) VALUES
    (1, 1, 1, 2, 1, '11111111-1111-1111-1111-111111111111', FALSE, NOW() - INTERVAL '4 days', $json${"channel":"slug","source":"web_app","ip_hash":"3f6f5c"}$json$::jsonb, NOW() - INTERVAL '4 days'),
    (2, 2, 1, 2, 1, '66666666-6666-6666-6666-666666666666', FALSE, NOW() - INTERVAL '3 days', $json${"channel":"public_link","source":"public_form"}$json$::jsonb, NOW() - INTERVAL '3 days'),
    (3, 4, 3, 5, 2, '33333333-3333-3333-3333-333333333333', FALSE, NOW() - INTERVAL '18 hours', $json${"channel":"public_link","campaign":"beta-april"}$json$::jsonb, NOW() - INTERVAL '18 hours');

-- =========================================
-- SUBMISSION ANSWERS
-- =========================================

INSERT INTO submission_answers (id, submission_id, question_key, answer_family, answer_value, created_at) VALUES
    (1, 1, 'engagement_score', 'rating', $json${"value":8}$json$::jsonb, NOW() - INTERVAL '4 days'),
    (2, 1, 'team_support', 'choice', $json${"selected":["very_supported"]}$json$::jsonb, NOW() - INTERVAL '4 days'),
    (3, 1, 'manager_feedback', 'field', $json${"value":"More frequent one-on-ones would help."}$json$::jsonb, NOW() - INTERVAL '4 days'),
    (4, 2, 'engagement_score', 'rating', $json${"value":6}$json$::jsonb, NOW() - INTERVAL '3 days'),
    (5, 2, 'team_support', 'choice', $json${"selected":["somewhat_supported"]}$json$::jsonb, NOW() - INTERVAL '3 days'),
    (6, 2, 'manager_feedback', 'field', $json${"value":"Clearer priorities across the week."}$json$::jsonb, NOW() - INTERVAL '3 days'),
    (7, 3, 'signup_ease', 'rating', $json${"value":9}$json$::jsonb, NOW() - INTERVAL '18 hours'),
    (8, 3, 'feature_interest', 'matching', $json${"matches":[{"left_id":"founder","right_id":"automation"},{"left_id":"marketer","right_id":"analytics"}]}$json$::jsonb, NOW() - INTERVAL '18 hours'),
    (9, 3, 'followup_email', 'field', $json${"value":"interested.user@example.test"}$json$::jsonb, NOW() - INTERVAL '18 hours');

-- =========================================
-- SUBMISSION EVENTS
-- =========================================

INSERT INTO submission_events (id, submission_id, event_type, event_payload, created_at) VALUES
    (1, 1, 'stored', $json${"destination":"platform_postgres","attempt":1}$json$::jsonb, NOW() - INTERVAL '4 days'),
    (2, 2, 'stored', $json${"destination":"platform_postgres","attempt":1}$json$::jsonb, NOW() - INTERVAL '3 days'),
    (3, 3, 'received', $json${"channel":"public_link"}$json$::jsonb, NOW() - INTERVAL '18 hours 5 minutes'),
    (4, 3, 'stored', $json${"destination":"platform_analytics","attempt":1}$json$::jsonb, NOW() - INTERVAL '18 hours');

-- =========================================
-- SEQUENCE RESET
-- =========================================

SELECT setval('submissions_id_seq', COALESCE((SELECT MAX(id) FROM submissions), 1), true);
SELECT setval('submission_answers_id_seq', COALESCE((SELECT MAX(id) FROM submission_answers), 1), true);
SELECT setval('submission_events_id_seq', COALESCE((SELECT MAX(id) FROM submission_events), 1), true);

COMMIT;
