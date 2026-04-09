-- Active: 1774882182463@@localhost@5433@flowform_response@response_app
-- =========================================
-- FLOWFORM RESPONSE DATABASE MOCK DATA
-- =========================================
-- Purpose:
-- - seeds realistic submission payloads for the response database
-- - aligns core_submission_id with the mock core seed file
--
-- Notes:
-- - insert this after the matching core mock data
-- - no cross-database foreign keys exist, so linkage is by agreed IDs only
-- - answer_value now follows the v1 JSON shape spec used by the tightened schema checks
--
-- Safe to run on an empty schema.

BEGIN;

-- =========================================
-- SUBMISSIONS
-- =========================================

INSERT INTO submissions (
    id,
    core_submission_id,
    survey_id,
    survey_version_id,
    project_id,
    pseudonymous_subject_id,
    is_anonymous,
    submitted_at,
    metadata,
    created_at
) VALUES
    (
        1,
        1,
        1,
        2,
        1,
        '11111111-1111-1111-1111-111111111111',
        FALSE,
        NOW() - INTERVAL '4 days',
        '{"channel":"authenticated","source":"web_app","ip_hash":"3f6f5c"}'::jsonb,
        NOW() - INTERVAL '4 days'
    ),
    (
        2,
        2,
        1,
        2,
        1,
        NULL,
        TRUE,
        NOW() - INTERVAL '3 days',
        '{"channel":"public_link","source":"public_form"}'::jsonb,
        NOW() - INTERVAL '3 days'
    ),
    (
        3,
        4,
        3,
        5,
        2,
        NULL,
        TRUE,
        NOW() - INTERVAL '18 hours',
        '{"channel":"public_link","campaign":"beta-april"}'::jsonb,
        NOW() - INTERVAL '18 hours'
    );

-- =========================================
-- SUBMISSION ANSWERS
-- =========================================

INSERT INTO submission_answers (
    id,
    submission_id,
    question_key,
    answer_family,
    answer_value,
    created_at
) VALUES
    (
        1,
        1,
        'engagement_score',
        'rating',
        '{"value":8}'::jsonb,
        NOW() - INTERVAL '4 days'
    ),
    (
        2,
        1,
        'team_support',
        'choice',
        '{"selected":["very_supported"]}'::jsonb,
        NOW() - INTERVAL '4 days'
    ),
    (
        3,
        1,
        'manager_feedback',
        'field',
        '{"value":"More frequent one-on-ones would help."}'::jsonb,
        NOW() - INTERVAL '4 days'
    ),
    (
        4,
        2,
        'engagement_score',
        'rating',
        '{"value":6}'::jsonb,
        NOW() - INTERVAL '3 days'
    ),
    (
        5,
        2,
        'team_support',
        'choice',
        '{"selected":["somewhat_supported"]}'::jsonb,
        NOW() - INTERVAL '3 days'
    ),
    (
        6,
        2,
        'manager_feedback',
        'field',
        '{"value":"Clearer priorities across the week."}'::jsonb,
        NOW() - INTERVAL '3 days'
    ),
    (
        7,
        3,
        'signup_ease',
        'rating',
        '{"value":9}'::jsonb,
        NOW() - INTERVAL '18 hours'
    ),
    (
        8,
        3,
        'feature_interest',
        'matching',
        '{"matches":[{"left_id":"founder","right_id":"automation"},{"left_id":"marketer","right_id":"analytics"}]}'::jsonb,
        NOW() - INTERVAL '18 hours'
    ),
    (
        9,
        3,
        'followup_email',
        'field',
        '{"value":"interested.user@example.test"}'::jsonb,
        NOW() - INTERVAL '18 hours'
    );

-- =========================================
-- SUBMISSION EVENTS
-- =========================================

INSERT INTO submission_events (
    id,
    submission_id,
    event_type,
    event_payload,
    created_at
) VALUES
    (
        1,
        1,
        'stored',
        '{"destination":"platform_postgres","attempt":1}'::jsonb,
        NOW() - INTERVAL '4 days'
    ),
    (
        2,
        2,
        'stored',
        '{"destination":"platform_postgres","attempt":1}'::jsonb,
        NOW() - INTERVAL '3 days'
    ),
    (
        3,
        3,
        'received',
        '{"channel":"public_link"}'::jsonb,
        NOW() - INTERVAL '18 hours 5 minutes'
    ),
    (
        4,
        3,
        'stored',
        '{"destination":"platform_analytics","attempt":1}'::jsonb,
        NOW() - INTERVAL '18 hours'
    );

-- =========================================
-- SEQUENCE RESET
-- =========================================

SELECT setval('submissions_id_seq', COALESCE((SELECT MAX(id) FROM submissions), 1), true);
SELECT setval('submission_answers_id_seq', COALESCE((SELECT MAX(id) FROM submission_answers), 1), true);
SELECT setval('submission_events_id_seq', COALESCE((SELECT MAX(id) FROM submission_events), 1), true);

COMMIT;
