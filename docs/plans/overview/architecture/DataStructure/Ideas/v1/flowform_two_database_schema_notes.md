# FlowForm two-database schema notes

## Main changes from your current schema

### 1. `survey_responses` is removed from the core database
Your current schema stores responses in one core table. In the new design, the core DB only keeps a lightweight registry in `survey_submissions`, and the raw answers move to the separate response DB.

### 2. survey definition is versioned
`survey_questions`, `survey_rules`, and `survey_scoring_rules` now point to `survey_versions` instead of directly to `surveys`.

That is important because responses should always map to the exact survey structure that was used at submission time.

### 3. response destinations are configurable
`response_stores` lets each project choose where responses are written:
- platform-managed Postgres
- customer-managed Postgres

### 4. pseudonymous subject IDs are supported
`response_subject_mappings` gives you a project-scoped pseudonymous identifier instead of writing the real `user_id` into the response DB.

### 5. raw answers are JSONB in the response database
This fits your question schema well because answer structures vary across question families such as choice, field, matching, and rating.

## Recommended write flow

1. Load published survey version from the core DB.
2. Validate the incoming answers against `survey_questions.question_schema` and the stored rules.
3. Create a row in `core.survey_submissions` with `status = 'pending'`.
4. Write the sensitive submission payload into `response_db.submissions` and `response_db.submission_answers`.
5. Update `core.survey_submissions` with:
   - `status = 'stored'`
   - `external_submission_id`
   - `submitted_at`
6. If the write fails, keep `status = 'failed'` and record `delivery_error`.

## Good first version

For v1, use:
- one platform-managed core Postgres database
- one separate platform-managed response Postgres database

Then later add customer-managed response stores.
