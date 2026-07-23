-- Active: 1774882182463@@localhost@5433@flowform_response@response_app
-- =========================================
-- FLOWFORM RESPONSE DATABASE MOCK DATA
-- =========================================
-- Purpose:
-- - seeds encrypted response envelopes/answers/revisions for the response database
-- - matches flowform_response_db_schema_v4.sql
-- - session_locator/answer_locator are dev-mode placeholders derived with
--   digest(), standing in for the real HMAC-SHA-256 locators. They line up
--   with the submission_sessions / survey_questions UUIDs from the core mock
--   seed (see flowform_core_mock_data.sql).
-- - wrapped_dek/ciphertext/nonce are placeholder bytes, not real ciphertext.
--
-- Safe to run on an empty schema after running the matching core mock data.

BEGIN;

-- =========================================
-- RESPONSE ENVELOPES
-- =========================================
-- One envelope per submission_sessions row (session_locator derived from the
-- core session UUID).

INSERT INTO response_envelopes (id, session_locator, linkage_key_version, wrapped_dek, kms_key_arn, kms_context_version, crypto_version) VALUES
    ('eeeeeeee-0000-0000-0000-000000000001', digest('aaaaaaaa-0000-0000-0000-000000000001', 'sha256'), 1, decode(repeat('aa', 32), 'hex'), 'arn:aws:kms:us-east-1:000000000000:key/dev-mock-key', 1, 1),
    ('eeeeeeee-0000-0000-0000-000000000002', digest('aaaaaaaa-0000-0000-0000-000000000002', 'sha256'), 1, decode(repeat('aa', 32), 'hex'), 'arn:aws:kms:us-east-1:000000000000:key/dev-mock-key', 1, 1),
    ('eeeeeeee-0000-0000-0000-000000000003', digest('aaaaaaaa-0000-0000-0000-000000000003', 'sha256'), 1, decode(repeat('aa', 32), 'hex'), 'arn:aws:kms:us-east-1:000000000000:key/dev-mock-key', 1, 1),
    ('eeeeeeee-0000-0000-0000-000000000004', digest('aaaaaaaa-0000-0000-0000-000000000004', 'sha256'), 1, decode(repeat('aa', 32), 'hex'), 'arn:aws:kms:us-east-1:000000000000:key/dev-mock-key', 1, 1);

-- =========================================
-- RESPONSE ANSWERS
-- =========================================
-- answer_locator derived from (session_uuid, question_node_id) so each
-- logical answer is unique within its envelope.

INSERT INTO response_answers (id, envelope_id, answer_locator, latest_revision_id) VALUES
    ('a1111111-0000-0000-0000-000000000001', 'eeeeeeee-0000-0000-0000-000000000001', digest('aaaaaaaa-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000001', 'sha256'), 'd1111111-0000-0000-0000-000000000001'),
    ('a1111111-0000-0000-0000-000000000002', 'eeeeeeee-0000-0000-0000-000000000001', digest('aaaaaaaa-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002', 'sha256'), 'd1111111-0000-0000-0000-000000000002'),

    ('a2222222-0000-0000-0000-000000000001', 'eeeeeeee-0000-0000-0000-000000000002', digest('aaaaaaaa-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003', 'sha256'), 'd2222222-0000-0000-0000-000000000001'),
    ('a2222222-0000-0000-0000-000000000002', 'eeeeeeee-0000-0000-0000-000000000002', digest('aaaaaaaa-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000005', 'sha256'), 'd2222222-0000-0000-0000-000000000002'),

    ('a4444444-0000-0000-0000-000000000001', 'eeeeeeee-0000-0000-0000-000000000004', digest('aaaaaaaa-0000-0000-0000-000000000004:00000000-0000-0000-0000-000000000011', 'sha256'), 'd4444444-0000-0000-0000-000000000001'),
    ('a4444444-0000-0000-0000-000000000002', 'eeeeeeee-0000-0000-0000-000000000004', digest('aaaaaaaa-0000-0000-0000-000000000004:00000000-0000-0000-0000-000000000012', 'sha256'), 'd4444444-0000-0000-0000-000000000002');

-- =========================================
-- RESPONSE ANSWER REVISIONS
-- =========================================
-- ciphertext/nonce are placeholder bytes, not real AES-GCM output.

INSERT INTO response_answer_revisions (id, answer_id, envelope_id, revision_number, ciphertext, nonce, client_mutation_id) VALUES
    -- session 1 (survey 1 v2): engagement_score, team_support
    ('d1111111-0000-0000-0000-000000000001', 'a1111111-0000-0000-0000-000000000001', 'eeeeeeee-0000-0000-0000-000000000001', 1, decode(repeat('11', 16), 'hex'), decode('111111111111111111111111', 'hex'), '11111111-aaaa-0000-0000-000000000001'),
    ('d1111111-0000-0000-0000-000000000002', 'a1111111-0000-0000-0000-000000000002', 'eeeeeeee-0000-0000-0000-000000000001', 1, decode(repeat('12', 16), 'hex'), decode('121212121212121212121212', 'hex'), '11111111-aaaa-0000-0000-000000000002'),

    -- session 2 (survey 1 v2): engagement_score, manager_feedback (with one revision)
    ('d2222222-0000-0000-0000-000000000001', 'a2222222-0000-0000-0000-000000000001', 'eeeeeeee-0000-0000-0000-000000000002', 1, decode(repeat('21', 16), 'hex'), decode('212121212121212121212121', 'hex'), '22222222-aaaa-0000-0000-000000000001'),
    ('d2222222-0000-0000-0000-000000000003', 'a2222222-0000-0000-0000-000000000002', 'eeeeeeee-0000-0000-0000-000000000002', 1, decode(repeat('22', 16), 'hex'), decode('222222222222222222222222', 'hex'), '22222222-aaaa-0000-0000-000000000003'),
    ('d2222222-0000-0000-0000-000000000002', 'a2222222-0000-0000-0000-000000000002', 'eeeeeeee-0000-0000-0000-000000000002', 2, decode(repeat('23', 16), 'hex'), decode('232323232323232323232323', 'hex'), '22222222-aaaa-0000-0000-000000000002'),

    -- session 4 (survey 3 v5): signup_ease, feature_interest
    ('d4444444-0000-0000-0000-000000000001', 'a4444444-0000-0000-0000-000000000001', 'eeeeeeee-0000-0000-0000-000000000004', 1, decode(repeat('41', 16), 'hex'), decode('414141414141414141414141', 'hex'), '44444444-aaaa-0000-0000-000000000001'),
    ('d4444444-0000-0000-0000-000000000002', 'a4444444-0000-0000-0000-000000000002', 'eeeeeeee-0000-0000-0000-000000000004', 1, decode(repeat('42', 16), 'hex'), decode('424242424242424242424242', 'hex'), '44444444-aaaa-0000-0000-000000000002');

COMMIT;
