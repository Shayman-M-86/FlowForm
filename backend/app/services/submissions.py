from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain import public_link_rules, submission_rules, survey_rules
from app.gateway.submission_gateway import SubmissionGateway
from app.repositories import public_link_repo, response_stores_repo, submissions_repo, surveys_repo
from app.schema.api.requests.submissions.create import LinkSubmissionRequest, SlugSubmissionRequest
from app.schema.api.requests.submissions.query import GetSubmissionRequest, ListSubmissionsRequest
from app.schema.orm.core.survey import Survey
from app.schema.orm.core.survey_submission import SurveySubmission
from app.schema.orm.core.user import User
from app.services.results import LinkedSubmissionResult

_gateway = SubmissionGateway()


@dataclass(slots=True)
class SubmissionContext:
    """Context object containing all data required to create a submission."""

    project_id: int
    survey_id: int
    survey_version_id: int
    response_store_id: int
    submission_channel: str
    submitted_by_user_id: int | None = None
    survey_link_id: int | None = None
    pseudonymous_subject_id: UUID | None = None
    is_anonymous: bool = False
    started_at: datetime | None = None
    submitted_at: datetime | None = None
    answers: list[dict] | None = None
    metadata: dict | None = None


class SubmissionIntakeService:
    """Respondent-facing submission intake service."""

    def _ensure_survey_response_store(
        self,
        core_db: Session,
        *,
        survey: Survey,
        created_by_user_id: int | None = None,
    ) -> int:
        if survey.default_response_store_id is not None:
            return survey.default_response_store_id

        store = response_stores_repo.get_or_create_platform_primary_store(
            core_db,
            survey.project_id,
            created_by_user_id=created_by_user_id,
        )
        survey.default_response_store_id = store.id
        return store.id

    def _resolve_subject_id(
        self,
        core_db: Session,
        *,
        project_id: int,
        submitted_by_user_id: int | None,
        is_anonymous: bool,
    ) -> UUID | None:
        if submitted_by_user_id is None or is_anonymous:
            return None

        mapping = _gateway.get_or_create_subject_mapping(
            core_db,
            project_id=project_id,
            user_id=submitted_by_user_id,
        )
        return mapping.pseudonymous_subject_id

    def create_link_submission(
        self,
        core_db: Session,
        response_db: Session,
        *,
        payload: LinkSubmissionRequest,
        actor: User,
    ) -> LinkedSubmissionResult:
        link = public_link_rules.ensure_is_not_none(link=public_link_repo.resolve_token(core_db, payload.token))
        public_link_rules.ensure_is_active(link=link)
        public_link_rules.ensure_not_expired(link=link)
        public_link_rules.ensure_actor_matches_assignment(link=link, actor_email=actor.email)

        survey = link.survey
        survey_rules.ensure_is_published(
            survey=survey,
            survey_id=survey.id,
            project_id=survey.project_id,
        )

        response_store_id = self._ensure_survey_response_store(
            core_db,
            survey=survey,
            created_by_user_id=actor.id,
        )

        context = SubmissionContext(
            project_id=survey.project_id,
            survey_id=survey.id,
            survey_version_id=payload.survey_version_id,
            response_store_id=response_store_id,
            submission_channel="link",
            submitted_by_user_id=actor.id,
            survey_link_id=link.id,
            pseudonymous_subject_id=self._resolve_subject_id(
                core_db,
                project_id=survey.project_id,
                submitted_by_user_id=actor.id,
                is_anonymous=False,
            ),
            is_anonymous=False,
            started_at=payload.started_at,
            submitted_at=payload.submitted_at,
            answers=[a.model_dump() for a in payload.answers],
            metadata=payload.metadata,
        )

        return self._create_submission_from_context(core_db, response_db, context=context)

    def create_slug_submission(
        self,
        core_db: Session,
        response_db: Session,
        *,
        payload: SlugSubmissionRequest,
        submitted_by_user_id: int | None = None,
    ) -> LinkedSubmissionResult:
        survey = survey_rules.ensure_found_by_slug(
            survey=surveys_repo.get_by_public_slug(core_db, payload.public_slug)
        )
        survey_rules.ensure_is_published(
            survey=survey,
            survey_id=survey.id,
            project_id=survey.project_id,
        )

        is_anonymous = submitted_by_user_id is None
        response_store_id = self._ensure_survey_response_store(
            core_db,
            survey=survey,
            created_by_user_id=submitted_by_user_id or survey.created_by_user_id,
        )

        context = SubmissionContext(
            project_id=survey.project_id,
            survey_id=survey.id,
            survey_version_id=payload.survey_version_id,
            response_store_id=response_store_id,
            submission_channel="slug",
            submitted_by_user_id=submitted_by_user_id,
            pseudonymous_subject_id=self._resolve_subject_id(
                core_db,
                project_id=survey.project_id,
                submitted_by_user_id=submitted_by_user_id,
                is_anonymous=is_anonymous,
            ),
            is_anonymous=is_anonymous,
            started_at=payload.started_at,
            submitted_at=payload.submitted_at,
            answers=[a.model_dump() for a in payload.answers],
            metadata=payload.metadata,
        )

        return self._create_submission_from_context(core_db, response_db, context=context)

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
            survey_link_id=context.survey_link_id,
            pseudonymous_subject_id=context.pseudonymous_subject_id,
            is_anonymous=context.is_anonymous,
            started_at=context.started_at,
            submitted_at=context.submitted_at,
            answers=context.answers,
            metadata=metadata,
        )


class SubmissionQueryService:
    """Project-facing submission review service."""

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


SubmissionService = SubmissionIntakeService
