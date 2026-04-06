import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.transaction import rollback_safely
from app.schema.orm.core.response_subject_mapping import ResponseSubjectMapping
from app.schema.orm.core.survey_submission import SurveySubmission
from app.schema.orm.response.submission import Submission
from app.schema.orm.response.submission_answer import SubmissionAnswer
from app.services.linked_submission import LinkedSubmission


class SubmissionGateway:
    """Cross-db coordinator for the submission saga workflow."""

    def get_or_create_subject_mapping(
        self,
        core_db: Session,
        *,
        project_id: int,
        user_id: int,
    ) -> ResponseSubjectMapping:
        mapping = core_db.scalar(
            select(ResponseSubjectMapping).where(
                ResponseSubjectMapping.project_id == project_id,
                ResponseSubjectMapping.user_id == user_id,
            )
        )
        if mapping is None:
            mapping = ResponseSubjectMapping(
                project_id=project_id,
                user_id=user_id,
                pseudonymous_subject_id=uuid.uuid4(),
            )
            core_db.add(mapping)
            core_db.flush()
        return mapping

    def create_linked_submission(
        self,
        core_db: Session,
        response_db: Session,
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
        started_at: datetime | None = None,
        submitted_at: datetime | None = None,
        answers: list[dict] | None = None,
        metadata: dict | None = None,
    ) -> LinkedSubmission:
        # Step 1-2: Create core registry row with pending status
        core_submission = SurveySubmission(
            project_id=project_id,
            survey_id=survey_id,
            survey_version_id=survey_version_id,
            response_store_id=response_store_id,
            submission_channel=submission_channel,
            submitted_by_user_id=submitted_by_user_id,
            public_link_id=public_link_id,
            pseudonymous_subject_id=pseudonymous_subject_id,
            is_anonymous=is_anonymous,
            started_at=started_at,
            submitted_at=submitted_at,
            status="pending",
        )
        core_db.add(core_submission)

        # Step 3: Flush to obtain the shared ID before writing to response DB
        core_db.flush()
        core_submission_id = core_submission.id

        # Steps 4-6: Write to response DB; on failure roll back and mark core failed
        try:
            response_submission = Submission(
                core_submission_id=core_submission_id,
                survey_id=survey_id,
                survey_version_id=survey_version_id,
                project_id=project_id,
                pseudonymous_subject_id=pseudonymous_subject_id,
                is_anonymous=is_anonymous,
                submitted_at=submitted_at,
                submission_metadata=metadata,
            )
            response_db.add(response_submission)
            response_db.flush()

            submission_answers: list[SubmissionAnswer] = []
            for ans in answers or []:
                sa = SubmissionAnswer(
                    submission_id=response_submission.id,
                    question_key=ans["question_key"],
                    answer_family=ans["answer_family"],
                    answer_value=ans["answer_value"],
                )
                response_db.add(sa)
                submission_answers.append(sa)

            response_db.commit()

        except Exception:
            rollback_safely(response_db)
            core_submission.status = "failed"
            core_db.commit()
            raise

        # Steps 7-8: Mark core as stored and commit
        core_submission.status = "stored"
        core_db.commit()

        return LinkedSubmission(
            core_submission=core_submission,
            response_submission=response_submission,
            subject_mapping=None,
            user=None,
            answers=submission_answers,
        )

    def load_linked_submission(
        self,
        core_db: Session,
        response_db: Session,
        *,
        core_submission_id: int,
        include_answers: bool = False,
        resolve_identity: bool = False,
    ) -> LinkedSubmission | None:
        from app.schema.orm.core.user import User

        core_submission = core_db.scalar(
            select(SurveySubmission).where(SurveySubmission.id == core_submission_id)
        )
        if core_submission is None:
            return None

        response_submission = response_db.scalar(
            select(Submission).where(Submission.core_submission_id == core_submission_id)
        )

        answers: list[SubmissionAnswer] = []
        if include_answers and response_submission is not None:
            answers = list(
                response_db.scalars(
                    select(SubmissionAnswer).where(
                        SubmissionAnswer.submission_id == response_submission.id
                    )
                )
            )

        subject_mapping: ResponseSubjectMapping | None = None
        user: User | None = None
        if (
            resolve_identity
            and response_submission is not None
            and response_submission.pseudonymous_subject_id is not None
        ):
            subject_mapping = core_db.scalar(
                select(ResponseSubjectMapping).where(
                    ResponseSubjectMapping.project_id == core_submission.project_id,
                    ResponseSubjectMapping.pseudonymous_subject_id
                    == response_submission.pseudonymous_subject_id,
                )
            )
            if subject_mapping is not None:
                user = core_db.scalar(
                    select(User).where(User.id == subject_mapping.user_id)
                )

        return LinkedSubmission(
            core_submission=core_submission,
            response_submission=response_submission,
            subject_mapping=subject_mapping,
            user=user,
            answers=answers,
        )
