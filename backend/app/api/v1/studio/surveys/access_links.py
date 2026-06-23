from uuid import UUID

from flask import g, request

from app.api.utils.validation import parse
from app.api.v1.studio.projects import studio_projects_bp, survey_link_service
from app.core.extensions import auth
from app.db.context import get_core_db
from app.domain.permissions import PERMISSIONS
from app.openapi import openapi_route
from app.schema.api.requests.survey_access_links import (
    CreateSurveyAccessLinkRequest,
    UpdateSurveyAccessLinkRequest,
)
from app.schema.api.responses.survey_access_links import (
    CreateSurveyAccessLinkResponse,
    ListSurveyAccessLinksResponse,
    SurveyAccessLinkResponse,
)
from app.services.access.access_service import require_survey_permission

_LBASE = "/<bint:project_id>/surveys/<bint:survey_id>/links"


@openapi_route(
    summary="List survey access links", response_model=ListSurveyAccessLinksResponse, tags=["Survey Access Links"]
)
@studio_projects_bp.route(_LBASE, methods=["GET"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.view)
def list_survey_access_links(project_id: int, survey_id: int):
    links = survey_link_service.list_links(db=get_core_db(), project_id=project_id, survey_id=survey_id, actor=g.actor)
    return ListSurveyAccessLinksResponse(
        links=[SurveyAccessLinkResponse.model_validate(link) for link in links]
    ).model_dump(mode="json"), 200


@openapi_route(
    summary="Create survey access link",
    request_model=CreateSurveyAccessLinkRequest,
    response_model=CreateSurveyAccessLinkResponse,
    status_code=201,
    tags=["Survey Access Links"],
)
@studio_projects_bp.route(_LBASE, methods=["POST"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.edit)
def create_survey_access_link(project_id: int, survey_id: int):
    payload = parse(CreateSurveyAccessLinkRequest, request)
    link = survey_link_service.create_link(
        db=get_core_db(),
        survey_id=survey_id,
        project_id=project_id,
        data=payload,
        actor=g.actor,
    )
    public_url = f"http://localhost:5173/quiz/resolve?token={link.token}"  # todo: construct URL based on config
    response = CreateSurveyAccessLinkResponse(
        link=SurveyAccessLinkResponse.model_validate(link),
        url=public_url,
    )
    return response.model_dump(mode="json"), 201


@openapi_route(
    summary="Update survey access link",
    request_model=UpdateSurveyAccessLinkRequest,
    response_model=SurveyAccessLinkResponse,
    tags=["Survey Access Links"],
)
@studio_projects_bp.route(f"{_LBASE}/<uuid:link_id>", methods=["PATCH"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.edit)
def update_survey_access_link(project_id: int, survey_id: int, link_id: UUID):
    payload = parse(UpdateSurveyAccessLinkRequest, request)
    updated_link = survey_link_service.update_link(
        db=get_core_db(),
        survey_id=survey_id,
        project_id=project_id,
        link_id=link_id,
        payload=payload,
        actor=g.actor,
    )
    return SurveyAccessLinkResponse.model_validate(updated_link).model_dump(mode="json"), 200


@openapi_route(summary="Delete survey access link", tags=["Survey Access Links"], status_code=204)
@studio_projects_bp.route(f"{_LBASE}/<uuid:link_id>", methods=["DELETE"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.edit)
def delete_survey_access_link(project_id: int, survey_id: int, link_id: UUID):
    survey_link_service.delete_link(
        db=get_core_db(), survey_id=survey_id, project_id=project_id, link_id=link_id, actor=g.actor
    )
    return "", 204
