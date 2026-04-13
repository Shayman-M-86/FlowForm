"""
Cross-database submission linkage tests.

FlowForm uses two separate PostgreSQL databases:

  core DB       — stores survey structure, projects, users, and submission metadata
                  (the survey_submissions table acts as a registry entry: channel,
                  status, timestamps, who submitted, which survey version was used)

  response DB   — stores the raw answer payloads in isolation, intentionally
                  separated so sensitive response data can be managed independently
                  (e.g. customer-managed Postgres, separate backup/retention policy)

The two sides are joined at the application layer using a single shared integer:

  core.survey_submissions.id  ←→  response.submissions.core_submission_id

There are no database-level foreign keys between the two databases — PostgreSQL
cannot enforce cross-database referential integrity. The application is responsible
for writing both records atomically and using core_submission_id to correlate them
when reading.

Privacy and pseudonymity
------------------------
For identified submissions, the real user_id is deliberately NOT written into
the response DB. Instead, a stable UUID is generated once per user+project and
stored in core.response_subject_mappings. That UUID — pseudonymous_subject_id —
is what gets written into response.submissions, keeping the answer payload store
free of directly identifying information.

The reverse lookup therefore goes:

  response.submission_answers
    → response.submissions.pseudonymous_subject_id
    → core.response_subject_mappings.user_id
    → core.users

1. Creates a ResponseSubjectMapping in the core DB — the one-time UUID assignment for this user+project
2. Creates an identified slug SurveySubmission in the core DB — this side holds the real user_id and the
pseudonymous_subject_id
3. Creates a Submission in the response DB — holds only pseudonymous_subject_id, never user_id
4. Creates a SubmissionAnswer in the response DB
5. Reverses the lookup in three steps: answer → pseudonymous_subject_id → ResponseSubjectMapping → User, confirming the
  identity can be recovered from the core DB without the response DB ever needing to know who the user is
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, scoped_session

from app.schema.orm.core.project import Project
from app.schema.orm.core.response_store import ResponseStore
from app.schema.orm.core.response_subject_mapping import ResponseSubjectMapping
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.survey_submission import SurveySubmission
from app.schema.orm.core.user import User
from app.schema.orm.response.submission import Submission
from app.schema.orm.response.submission_answer import SubmissionAnswer


def test_core_submission_links_to_response_submission(
    db_session: scoped_session[Session],
    project: Project,
    response_store: ResponseStore,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    """Core SurveySubmission and response Submission are linked via core_submission_id."""
    # Write the registry entry to the core DB (system channel — no user or link required)
    core_submission = SurveySubmission()
    core_submission.project_id = project.id
    core_submission.survey_id = survey.id
    core_submission.survey_version_id = survey_version.id
    core_submission.response_store_id = response_store.id
    core_submission.submission_channel = "system"
    db_session.add(core_submission)
    db_session.flush()

    assert core_submission.id is not None, "SurveySubmission was not persisted in the core DB"

    # Write the answer payload record to the response DB, linking back via core_submission_id
    response_submission = Submission()
    response_submission.core_submission_id = core_submission.id
    response_submission.survey_id = survey.id
    response_submission.survey_version_id = survey_version.id
    response_submission.project_id = project.id
    db_session.add(response_submission)
    db_session.flush()

    assert response_submission.id is not None, "Submission was not persisted in the response DB"
    assert response_submission.core_submission_id == core_submission.id, (
        f"core_submission_id={response_submission.core_submission_id!r}, expected {core_submission.id!r}"
    )

    # Round-trip: use the ID stored in the response DB to look up the original core record
    looked_up = db_session.get(SurveySubmission, response_submission.core_submission_id)
    assert looked_up is not None, (
        f"Could not find SurveySubmission with id={response_submission.core_submission_id!r} in the core DB"
    )
    assert looked_up.survey_id == survey.id, (
        f"looked_up.survey_id={looked_up.survey_id!r}, expected {survey.id!r}"
    )


def test_answer_can_be_traced_back_to_user_via_pseudonymous_subject_id(
    db_session: scoped_session[Session],
    user: User,
    project: Project,
    response_store: ResponseStore,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    """
    An answer in the response DB can be traced back to the submitting user in the
    core DB via pseudonymous_subject_id — without the response DB ever holding the
    real user_id.
    """
    # Assign the user a stable pseudonymous UUID for this project
    mapping = ResponseSubjectMapping()
    mapping.project_id = project.id
    mapping.user_id = user.id
    mapping.pseudonymous_subject_id = uuid.uuid4()
    db_session.add(mapping)
    db_session.flush()

    # Write the core submission registry entry — identified slug submissions record the real user_id
    core_submission = SurveySubmission()
    core_submission.project_id = project.id
    core_submission.survey_id = survey.id
    core_submission.survey_version_id = survey_version.id
    core_submission.response_store_id = response_store.id
    core_submission.submission_channel = "slug"
    core_submission.submitted_by_user_id = user.id
    core_submission.pseudonymous_subject_id = mapping.pseudonymous_subject_id
    db_session.add(core_submission)
    db_session.flush()

    # Write the response submission — pseudonymous_subject_id only, no user_id
    response_submission = Submission()
    response_submission.core_submission_id = core_submission.id
    response_submission.survey_id = survey.id
    response_submission.survey_version_id = survey_version.id
    response_submission.project_id = project.id
    response_submission.pseudonymous_subject_id = mapping.pseudonymous_subject_id
    db_session.add(response_submission)
    db_session.flush()

    # Write an answer
    answer = SubmissionAnswer()
    answer.submission_id = response_submission.id
    answer.question_key = "q1"
    answer.answer_family = "field"
    answer.answer_value = {"value": "hello"}
    db_session.add(answer)
    db_session.flush()

    # --- Reverse lookup ---
    # Step 1: from the answer, get the submission's pseudonymous_subject_id
    saved_answer = db_session.get(SubmissionAnswer, answer.id)
    assert saved_answer is not None, "SubmissionAnswer was not persisted"

    saved_submission = db_session.get(Submission, saved_answer.submission_id)
    assert saved_submission is not None, "Submission was not found"
    subject_id = saved_submission.pseudonymous_subject_id

    # Step 2: look up the mapping in the core DB to recover the user_id
    found_mapping = db_session.scalars(
        select(ResponseSubjectMapping).where(
            ResponseSubjectMapping.project_id == project.id,
            ResponseSubjectMapping.pseudonymous_subject_id == subject_id,
        )
    ).one()

    assert found_mapping.user_id == user.id, (
        f"Traced user_id={found_mapping.user_id!r} via pseudonymous_subject_id, expected {user.id!r}"
    )

    # Step 3: confirm we can load the actual User record
    found_user = db_session.get(User, found_mapping.user_id)
    assert found_user is not None, "User was not found in the core DB"
    assert found_user.id == user.id, f"found_user.id={found_user.id!r}, expected {user.id!r}"
