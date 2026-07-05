from flask import request

from app.api.utils.submission_session_cookie import get_recognition_token, set_recognition_cookie
from app.api.utils.validation import parse
from app.api.v1.respondent import respondent_bp, survey_resolve_service, users_service
from app.core.extensions import auth
from app.db.context import get_core_db
from app.openapi import openapi_route
from app.schema.api.requests.survey_access_links import ResolveSurveyAccessLinkTokenRequest
from app.schema.api.responses.survey_access_links import (
    ResolveSurveyAccessLinkResponse,
    SurveyAccessLinkResponse,
)
from app.schema.api.responses.surveys import SurveyResponses, SurveyVersionResponses


@openapi_route(
    summary="Resolve survey access link",
    request_model=ResolveSurveyAccessLinkTokenRequest,
    response_model=ResolveSurveyAccessLinkResponse,
    tags=["Respondent Links"],
    auth="optional",
    description=(
        "Anonymous access is allowed for links that do not require authentication. "
        "If the resolved link requires authentication, a bearer token must be supplied."
    ),
)
@respondent_bp.route("/links/resolve", methods=["POST"])
@auth.optional_auth()
def resolve_link():
    payload = parse(ResolveSurveyAccessLinkTokenRequest, request)

    core_db = get_core_db()

    current_sub = auth.get_optional_current_user_sub()
    user = users_service.get_user_by_sub(db=core_db, auth0_user_id=current_sub) if current_sub is not None else None
    result = survey_resolve_service.resolve_link(core_db, payload=payload, actor=user)
    response = ResolveSurveyAccessLinkResponse(
        link=SurveyAccessLinkResponse.model_validate(result.link),
        survey=SurveyResponses.model_validate(result.survey),
        published_version=SurveyVersionResponses.model_validate(result.published_version),
    )

    return response.model_dump(mode="json"), 200


@openapi_route(
    summary="Verify authenticated survey link participant",
    request_model=ResolveSurveyAccessLinkTokenRequest,
    response_model=SurveyAccessLinkResponse,
    tags=["Respondent Links"],
    auth_required=True,
    description=(
        "Verify the authenticated account against the participant assigned to "
        "an authenticated survey link. The account email must match the "
        "participant identity email before the participant is linked to the user."
    ),
)
@respondent_bp.route("/links/verification/link", methods=["POST"])
@auth.require_auth()
def verify_authenticated_link_participant():
    payload = parse(ResolveSurveyAccessLinkTokenRequest, request)
    core_db = get_core_db()
    user = users_service.get_user_by_sub(db=core_db, auth0_user_id=auth.get_current_user_sub())
    result = survey_resolve_service.verify_authenticated_link_participant(
        core_db,
        payload=payload,
        actor=user,
        recognition_token=get_recognition_token(),
    )
    response = SurveyAccessLinkResponse.model_validate(result.link)
    flask_response = response.model_dump(mode="json"), 200
    if result.raw_recognition_token is not None:
        set_recognition_cookie(result.raw_recognition_token)
    return flask_response
