# Validation Ladder

Prefer focused validation after each pass:

```bash
bash scripts/run-tests.sh --ai -k "<focused selector>"
```

Climb ladder as risk rises:

1. Unit tests for result contracts and repository helpers.
2. Service tests for access, subject, and token decisions.
3. Scenario-table tests for flow matrix.
4. Integration tests for each access method.
5. Route tests for cookies and public response contracts.
6. OpenAPI/schema tests after response contract changes.
7. Broader backend validation after shared domain, auth, token, transaction, or
   repository behavior changes.

Useful selectors to build or maintain:

* `survey_access_resolver`
* `subject_token`
* `subject_resolution`
* `submission_session_starter`
* `authenticated_link`
* `public_submission`

Record skipped validation in pass report. Skipped validation is not green.
