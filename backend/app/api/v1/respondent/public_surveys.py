from flask import request

from app.api.utils.validation import parse_query
from app.api.v1.respondent import respondent_bp, survey_resolve_service
from app.db.context import get_core_db
from app.openapi import openapi_route
from app.schema.api.requests.surveys import ListPublicSurveysRequest
from app.schema.api.responses.surveys import (
    PaginatedPublicSurveysResponses,
    PublicSurveyResponses,
    SurveyResponses,
    SurveyVersionResponses,
)


@openapi_route(
    summary="List public surveys",
    query_model=ListPublicSurveysRequest,
    response_model=PaginatedPublicSurveysResponses,
    tags=["Respondent Surveys"],
    auth_required=False,
)
@respondent_bp.route("/surveys", methods=["GET"])
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
    tags=["Respondent Surveys"],
    auth_required=False,
)
@respondent_bp.route("/surveys/<public_slug:public_slug>", methods=["GET"])
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
