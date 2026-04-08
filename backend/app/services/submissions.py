from dataclasses import dataclass
from datetime import datetime
from logging import getLogger
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain import public_link_rules, submission_rules, survey_rules
from app.gateway.submission_gateway import SubmissionGateway
from app.repositories import public_link_repo, submissions_repo, surveys_repo
from app.schema.api.requests.submissions.create import CreateSubmissionRequest, PublicSubmissionRequest
from app.schema.api.requests.submissions.query import GetSubmissionRequest, ListSubmissionsRequest
from app.schema.orm.core.survey_submission import SurveySubmission
from app.services.results import LinkedSubmissionResult

logger = getLogger(__name__)
_gateway = SubmissionGateway()


@dataclass(slots=True)
class SubmissionContext:
    """Context object containing all necessary information to create a submission, passed to the gateway layer."""

    project_id: int
    survey_id: int
    survey_version_id: int
    response_store_id: int
    submission_channel: str
    submitted_by_user_id: int | None = None
    public_link_id: int | None = None
    pseudonymous_subject_id: UUID | None = None
    is_anonymous: bool = False
    started_at: datetime | None = None
    submitted_at: datetime | None = None
    answers: list[dict] | None = None
    metadata: dict | None = None


class SubmissionService:
    """Service layer handling survey submissions, both from authenticated users and via public links."""

    def create_project_submission(
        self,
        core_db: Session,
        response_db: Session,
        *,
        project_id: int,
        survey_id: int,
        payload: CreateSubmissionRequest,
    ) -> LinkedSubmissionResult:
        survey = survey_rules.ensure_not_none(
            survey=surveys_repo.get_survey(core_db, project_id=project_id, survey_id=survey_id),
            survey_id=survey_id,
            project_id=project_id,
        )
        logger.info(f"Creating submission for survey_id={survey_id} in project_id={project_id}")
        survey_rules.ensure_is_published(
            survey=survey,
            survey_id=survey_id,
            project_id=project_id,
        )
        response_store_id = survey_rules.ensure_has_response_store(survey=survey)
        logger.info(f"Survey {survey_id} in project {project_id} is published, proceeding with submission creation")

        pseudonymous_subject_id = None
        if payload.submitted_by_user_id is not None and not payload.is_anonymous:
            mapping = _gateway.get_or_create_subject_mapping(
                core_db,
                project_id=project_id,
                user_id=payload.submitted_by_user_id,
            )
            logger.info(
                f"Created or retrieved subject mapping for user_id={payload.submitted_by_user_id} "
                f"in project_id={project_id}"
            )
            pseudonymous_subject_id = mapping.pseudonymous_subject_id

        context = SubmissionContext(
            project_id=project_id,
            survey_id=survey_id,
            survey_version_id=payload.survey_version_id,
            response_store_id=response_store_id,
            submission_channel=submission_rules.resolve_submission_channel(
                submitted_by_user_id=payload.submitted_by_user_id,
            ),
            submitted_by_user_id=payload.submitted_by_user_id,
            pseudonymous_subject_id=pseudonymous_subject_id,
            is_anonymous=payload.is_anonymous,
            started_at=payload.started_at,
            submitted_at=payload.submitted_at,
            answers=[a.model_dump() for a in payload.answers],
            metadata=payload.metadata,
        )

        return self._create_submission_from_context(
            core_db,
            response_db,
            context=context,
        )

    def create_public_submission(
        self,
        core_db: Session,
        response_db: Session,
        *,
        payload: PublicSubmissionRequest,
    ) -> LinkedSubmissionResult:
        link = public_link_rules.ensure_is_not_none(link=public_link_repo.resolve_token(core_db, payload.public_token))
        public_link_rules.ensure_is_active(link=link)
        public_link_rules.ensure_allows_response(link=link)
        public_link_rules.ensure_not_expired(link=link)

        survey = link.survey
        survey_rules.ensure_is_published(
            survey=survey,
            survey_id=survey.id,
            project_id=survey.project_id,
        )
        response_store_id = survey_rules.ensure_has_response_store(survey=survey)

        context = SubmissionContext(
            project_id=survey.project_id,
            survey_id=survey.id,
            survey_version_id=payload.survey_version_id,
            response_store_id=response_store_id,
            submission_channel="public_link",
            public_link_id=link.id,
            is_anonymous=payload.is_anonymous,
            started_at=payload.started_at,
            submitted_at=payload.submitted_at,
            answers=[a.model_dump() for a in payload.answers],
            metadata=payload.metadata,
        )

        return self._create_submission_from_context(
            core_db,
            response_db,
            context=context,
        )

    def _create_submission_from_context(
        self,
        core_db: Session,
        response_db: Session,
        *,
        context: SubmissionContext,
    ) -> LinkedSubmissionResult:
        metadata = context.metadata or {}
        return _gateway.create_linked_submission(
            core_db,
            response_db,
            project_id=context.project_id,
            survey_id=context.survey_id,
            survey_version_id=context.survey_version_id,
            response_store_id=context.response_store_id,
            submission_channel=context.submission_channel,
            submitted_by_user_id=context.submitted_by_user_id,
            public_link_id=context.public_link_id,
            pseudonymous_subject_id=context.pseudonymous_subject_id,
            is_anonymous=context.is_anonymous,
            started_at=context.started_at,
            submitted_at=context.submitted_at,
            answers=context.answers,
            metadata=metadata,
        )

    def list_submissions(
        self,
        db: Session,
        *,
        project_id: int,
        payload: ListSubmissionsRequest,
    ) -> tuple[list[SurveySubmission], int]:
        return submissions_repo.list_submissions(
            db,
            project_id=project_id,
            survey_id=payload.survey_id,
            status=payload.status,
            submission_channel=payload.submission_channel,
            page=payload.page,
            page_size=payload.page_size,
        )

    def get_submission(
        self,
        core_db: Session,
        response_db: Session,
        *,
        project_id: int,
        submission_id: int,
        params: GetSubmissionRequest,
    ) -> LinkedSubmissionResult:
        linked = _gateway.load_linked_submission(
            core_db,
            response_db,
            core_submission_id=submission_id,
            include_answers=params.include_answers,
            resolve_identity=params.resolve_identity,
        )

        linked = submission_rules.ensure_submission_exists(
            linked=linked,
            submission_id=submission_id,
        )

        submission_rules.ensure_submission_belongs_to_project(
            linked=linked,
            project_id=project_id,
            submission_id=submission_id,
        )

        return linked
