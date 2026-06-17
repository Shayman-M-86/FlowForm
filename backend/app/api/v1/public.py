from datetime import UTC, datetime
from logging import getLogger

from flask import Blueprint, request

from app.api.utils.submission_session_cookie import (
    get_recognition_token,
    set_recognition_cookie,
    set_submission_session_cookie,
)
from app.api.utils.validation import parse, parse_query
from app.core.extensions import auth
from app.db.context import get_core_db, get_response_db
from app.openapi import openapi_route
from app.schema.api.requests.public_links import ResolveTokenRequest
from app.schema.api.requests.submission_sessions import (
    SaveSubmissionSessionAnswerRequest,
    StartSubmissionSessionRequest,
    SubmissionSessionEventRequest,
)
from app.schema.api.requests.surveys import ListPublicSurveysRequest
from app.schema.api.responses.public_links import PublicLinkResponses, ResolveLinkResponses
from app.schema.api.responses.submission_sessions import (
    CompleteSubmissionSessionResponses,
    PublicSubmissionSessionResponses,
    SubmissionSessionAnswerResponses,
)
from app.schema.api.responses.surveys import (
    PaginatedPublicSurveysResponses,
    PublicSurveyResponses,
    SurveyResponses,
    SurveyVersionResponses,
)
from app.services.public_submissions.api.session_management import SessionManagementService
from app.services.public_submissions.api.survey_resolve import SurveyResolveService
from app.services.users import UserService

logger = getLogger(__name__)

public_bp = Blueprint("public_v1", __name__)

users_service = UserService()
survey_resolve_service = SurveyResolveService()
session_management_service = SessionManagementService()


@openapi_route(
    summary="List public surveys",
    query_model=ListPublicSurveysRequest,
    response_model=PaginatedPublicSurveysResponses,
    tags=["Public"],
    auth_required=False,
)
@public_bp.route("/surveys", methods=["GET"])
def list_public_surveys():
    params = parse_query(ListPublicSurveysRequest, request)
    core_db = get_core_db()

    result = survey_resolve_service.list_public_surveys(core_db, page=params.page, page_size=params.page_size)
    response = PaginatedPublicSurveysResponses(
        items=[SurveyResponses.model_validate(s) for s in result.surveys],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )
    return response.model_dump(mode="json"), 200


@openapi_route(
    summary="Get public survey",
    response_model=PublicSurveyResponses,
    tags=["Public"],
    auth_required=False,
)
@public_bp.route("/surveys/<public_slug:public_slug>", methods=["GET"])
def get_public_survey(public_slug: str):
    core_db = get_core_db()

    result = survey_resolve_service.get_public_survey(core_db, public_slug=public_slug)
    response = PublicSurveyResponses(
        survey=SurveyResponses.model_validate(result.survey),
        published_version=(
            SurveyVersionResponses.model_validate(result.published_version) if result.published_version else None
        ),
    )
    return response.model_dump(mode="json"), 200


@openapi_route(
    summary="Resolve survey link",
    request_model=ResolveTokenRequest,
    response_model=ResolveLinkResponses,
    tags=["Public Links"],
    auth="optional",
    description=(
        "Anonymous access is allowed for links that do not require authentication. "
        "If the resolved link requires authentication, a bearer token must be supplied."
    ),
)
@public_bp.route("/links/resolve", methods=["POST"])
@auth.optional_auth()
def resolve_link():
    payload = parse(ResolveTokenRequest, request)

    core_db = get_core_db()

    current_sub = auth.get_optional_current_user_sub()
    user = users_service.get_user_by_sub(db=core_db, auth0_user_id=current_sub) if current_sub is not None else None
    result = survey_resolve_service.resolve_link(core_db, payload=payload, actor=user)
    response = ResolveLinkResponses(
        link=PublicLinkResponses.model_validate(result.link),
        survey=SurveyResponses.model_validate(result.survey),
        published_version=SurveyVersionResponses.model_validate(result.published_version),
    )

    return response.model_dump(mode="json"), 200


@openapi_route(
    summary="Verify authenticated survey link participant",
    request_model=ResolveTokenRequest,
    response_model=PublicLinkResponses,
    tags=["Public Links"],
    auth_required=True,
    description=(
        "Verify the authenticated account against the participant assigned to "
        "an authenticated survey link. The account email must match the "
        "participant identity email before the participant is linked to the user."
    ),
)
@public_bp.route("/links/verification/link", methods=["POST"])
@auth.require_auth()
def verify_authenticated_link_participant():
    payload = parse(ResolveTokenRequest, request)
    core_db = get_core_db()
    user = users_service.get_user_by_sub(db=core_db, auth0_user_id=auth.get_current_user_sub())
    result = survey_resolve_service.verify_authenticated_link_participant(
        core_db,
        payload=payload,
        actor=user,
        recognition_token=get_recognition_token(),
    )
    response = PublicLinkResponses.model_validate(result.link)
    flask_response = response.model_dump(mode="json"), 200
    if result.raw_recognition_token is not None:
        set_recognition_cookie(result.raw_recognition_token)
    return flask_response


@openapi_route(
    summary="Start submission session",
    request_model=StartSubmissionSessionRequest,
    response_model=PublicSubmissionSessionResponses,
    status_code=201,
    tags=["Public Submission Sessions"],
    auth="optional",
)
@public_bp.route("/submission-session/start", methods=["POST"])
@auth.optional_auth()
def start_submission_session():
    payload = parse(StartSubmissionSessionRequest, request)
    core_db = get_core_db()
    current_sub = auth.get_optional_current_user_sub()
    user = users_service.get_user_by_sub(db=core_db, auth0_user_id=current_sub) if current_sub is not None else None
    response_db = get_response_db()
    response, raw_browser_session_token, raw_recognition_token = session_management_service.start_session(
        core_db,
        response_db,
        payload=payload,
        actor=user,
        recognition_token=get_recognition_token(),
    )
    set_submission_session_cookie(raw_browser_session_token)
    if raw_recognition_token is not None:
        set_recognition_cookie(raw_recognition_token)
    return response.model_dump(mode="json"), 201


# TODO(phase4): Rework this placeholder to validate against the frozen survey
# version and create encrypted response answer revisions.
@openapi_route(
    summary="Save submission session answer",
    request_model=SaveSubmissionSessionAnswerRequest,
    response_model=SubmissionSessionAnswerResponses,
    tags=["Public Submission Sessions"],
    auth_required=False,
)
@public_bp.route("/submission-session/answer", methods=["PUT"])
def save_submission_session_answer():
    payload = parse(SaveSubmissionSessionAnswerRequest, request)
    response = SubmissionSessionAnswerResponses(
        question_node_id=payload.question_node_id,
        state=payload.state,
        answer_family=payload.answer_family,
        answer_value=payload.answer_value,
        revision_number=1,
        client_mutation_id=payload.client_mutation_id,
        saved_at=datetime.now(UTC),
    )
    return response.model_dump(mode="json"), 200


# TODO(phase3): Rework this placeholder to persist core-side analytics events;
# event write failures should stay secondary to the respondent flow.
@openapi_route(
    summary="Record submission session event",
    request_model=SubmissionSessionEventRequest,
    status_code=204,
    tags=["Public Submission Sessions"],
    auth_required=False,
)
@public_bp.route("/submission-session/event", methods=["POST"])
def record_submission_session_event():
    parse(SubmissionSessionEventRequest, request)
    return "", 204


# TODO(phase5): Rework this placeholder to complete the core session
# idempotently and reject later answer edits.
@openapi_route(
    summary="Complete submission session",
    response_model=CompleteSubmissionSessionResponses,
    tags=["Public Submission Sessions"],
    auth_required=False,
)
@public_bp.route("/submission-session/complete", methods=["POST"])
def complete_submission_session():
    response = CompleteSubmissionSessionResponses(status="completed", completed_at=datetime.now(UTC))
    return response.model_dump(mode="json"), 200
