from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.transaction import commit_or_rollback, rollback_safely
from app.schema.orm.core.response_subject_mapping import ResponseSubjectMapping
from app.schema.orm.core.survey_submission import SurveySubmission
from app.schema.orm.core.user import User
from app.schema.orm.response.submission import Submission
from app.schema.orm.response.submission_answer import SubmissionAnswer
from app.services.linked_submission import LinkedSubmission


class SubmissionGateway:
    """Orchestrates cross-database submission workflows.

    This is the main coordination layer for creating and loading linked
    submissions that span the core and response databases. It implements a
    saga-style workflow to handle the absence of cross-database atomic
    transactions.

    Caller is responsible for providing open sessions. The gateway commits
    both sessions on success and handles rollback/failure-status on error.
    """

    # ------------------------------------------------------------------
    # Subject mapping
    # ------------------------------------------------------------------

    def get_or_create_subject_mapping(
        self,
        core_session: Session,
        *,
        project_id: int,
        user_id: int,
    ) -> ResponseSubjectMapping:
        """Return the existing mapping or create a new pseudonymous UUID for a user+project pair."""
        mapping = core_session.scalars(
            select(ResponseSubjectMapping).where(
                ResponseSubjectMapping.project_id == project_id,
                ResponseSubjectMapping.user_id == user_id,
            )
        ).one_or_none()

        if mapping is None:
            mapping = ResponseSubjectMapping()
            mapping.project_id = project_id
            mapping.user_id = user_id
            mapping.pseudonymous_subject_id = uuid.uuid4()
            core_session.add(mapping)
            core_session.flush()

        return mapping

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_linked_submission(
        self,
        core_session: Session,
        response_session: Session,
        *,
        project_id: int,
        survey_id: int,
        survey_version_id: int,
        response_store_id: int,
        submission_channel: str,
        submitted_by_user_id: int | None = None,
        public_link_id: int | None = None,
        pseudonymous_subject_id: uuid.UUID | None = None,
        is_anonymous: bool = False,
        answers: list[dict] | None = None,
        submission_metadata: dict | None = None,
    ) -> LinkedSubmission:
        """Create a linked submission across both databases using a saga workflow.

        Saga steps
        ----------
        1. Create ``SurveySubmission`` in core with ``status='pending'``
        2. Flush core to obtain the shared integer ID
        3. Create ``Submission`` in response DB using ``core_submission_id``
        4. Create ``SubmissionAnswer`` rows (if provided)
        5. Commit response DB
        6. Update core submission ``status`` to ``'stored'``
        7. Commit core DB

        Failure path
        ------------
        If any response-side step raises, the response session is rolled back,
        the core submission is updated to ``status='failed'``, and the core
        session is committed so the failed record is recoverable.
        """
        # Step 1 — core registry entry (pending)
        core_submission = SurveySubmission()
        core_submission.project_id = project_id
        core_submission.survey_id = survey_id
        core_submission.survey_version_id = survey_version_id
        core_submission.response_store_id = response_store_id
        core_submission.submission_channel = submission_channel
        core_submission.submitted_by_user_id = submitted_by_user_id
        core_submission.public_link_id = public_link_id
        core_submission.pseudonymous_subject_id = pseudonymous_subject_id
        core_submission.is_anonymous = is_anonymous
        core_submission.status = "pending"
        core_session.add(core_submission)

        # Step 2 — flush to materialise the ID
        core_session.flush()

        response_submission = Submission()
        response_answers: list[SubmissionAnswer] = []

        try:
            # Step 3 — response payload record
            response_submission.core_submission_id = core_submission.id
            response_submission.survey_id = survey_id
            response_submission.survey_version_id = survey_version_id
            response_submission.project_id = project_id
            response_submission.pseudonymous_subject_id = pseudonymous_subject_id
            response_submission.is_anonymous = is_anonymous
            if submission_metadata is not None:
                response_submission.submission_metadata = submission_metadata
            response_session.add(response_submission)
            response_session.flush()

            # Step 4 — answer rows
            if answers:
                for answer_data in answers:
                    answer = SubmissionAnswer()
                    answer.submission_id = response_submission.id
                    answer.question_key = answer_data["question_key"]
                    answer.answer_family = answer_data["answer_family"]
                    answer.answer_value = answer_data["answer_value"]
                    response_session.add(answer)
                    response_answers.append(answer)
                response_session.flush()

            # Step 5 — commit response
            commit_or_rollback(response_session)

        except Exception:
            rollback_safely(response_session)
            core_submission.status = "failed"
            commit_or_rollback(core_session)
            raise

        # Step 6 — mark stored
        core_submission.status = "stored"

        # Step 7 — commit core
        commit_or_rollback(core_session)

        return LinkedSubmission(
            core_submission=core_submission,
            response_submission=response_submission,
            answers=response_answers,
        )

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load_linked_submission(
        self,
        core_session: Session,
        response_session: Session,
        *,
        core_submission_id: int,
        include_answers: bool = False,
        resolve_identity: bool = False,
    ) -> LinkedSubmission | None:
        """Load a linked submission by core submission ID.

        Returns ``None`` if either the core or response record is missing.

        Parameters
        ----------
        include_answers:
            When ``True``, eagerly loads ``SubmissionAnswer`` rows from the
            response DB.
        resolve_identity:
            When ``True``, follows the reverse-lookup chain to populate
            ``subject_mapping`` and ``user``:

            response.submissions.pseudonymous_subject_id
              -> core.response_subject_mappings.user_id
              -> core.users
        """
        core_submission = core_session.get(SurveySubmission, core_submission_id)
        if core_submission is None:
            return None

        response_submission = response_session.scalars(
            select(Submission).where(
                Submission.core_submission_id == core_submission_id
            )
        ).one_or_none()
        if response_submission is None:
            return None

        subject_mapping: ResponseSubjectMapping | None = None
        user: User | None = None
        answers: list[SubmissionAnswer] = []

        if resolve_identity and response_submission.pseudonymous_subject_id is not None:
            subject_mapping = core_session.scalars(
                select(ResponseSubjectMapping).where(
                    ResponseSubjectMapping.project_id == core_submission.project_id,
                    ResponseSubjectMapping.pseudonymous_subject_id
                    == response_submission.pseudonymous_subject_id,
                )
            ).one_or_none()
            if subject_mapping is not None:
                user = core_session.get(User, subject_mapping.user_id)

        if include_answers:
            answers = list(
                response_session.scalars(
                    select(SubmissionAnswer).where(
                        SubmissionAnswer.submission_id == response_submission.id
                    )
                ).all()
            )

        return LinkedSubmission(
            core_submission=core_submission,
            response_submission=response_submission,
            subject_mapping=subject_mapping,
            user=user,
            answers=answers,
        )
