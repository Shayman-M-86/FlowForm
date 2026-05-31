from flask import g, request

from app.api.utils.validation import parse
from app.api.v1.projects import projects_bp, survey_link_service
from app.core.extensions import auth
from app.db.context import get_core_db
from app.domain.permissions import PERMISSIONS
from app.openapi import openapi_route
from app.schema.api.requests.public_links import CreatePublicLinkRequest, UpdatePublicLinkRequest
from app.schema.api.responses.public_links import (
    CreatePublicLinkResponses,
    ListPublicLinksResponses,
    PublicLinkResponses,
)
from app.services.access.access_service import require_survey_permission

_LBASE = "/<bint:project_id>/surveys/<bint:survey_id>/links"


@openapi_route(summary="List survey links", response_model=ListPublicLinksResponses, tags=["Survey Links"])
@projects_bp.route(_LBASE, methods=["GET"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.view)
def list_public_links(project_id: int, survey_id: int):
    links = survey_link_service.list_links(db=get_core_db(), project_id=project_id, survey_id=survey_id, actor=g.actor)
    return ListPublicLinksResponses(links=[PublicLinkResponses.model_validate(link) for link in links]).model_dump(
        mode="json"
    ), 200


@openapi_route(
    summary="Create survey link",
    request_model=CreatePublicLinkRequest,
    response_model=CreatePublicLinkResponses,
    status_code=201,
    tags=["Survey Links"],
)
@projects_bp.route(_LBASE, methods=["POST"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.edit)
def create_public_link(project_id: int, survey_id: int):
    payload = parse(CreatePublicLinkRequest, request)
    result = survey_link_service.create_link(
        db=get_core_db(),
        survey_id=survey_id,
        project_id=project_id,
        data=payload,
        actor=g.actor,
    )
    public_url = f"http://localhost:5173/quiz/resolve?token={result.token}"  # todo: construct URL based on config
    response = CreatePublicLinkResponses(
        link=PublicLinkResponses.model_validate(result.link),
        token=result.token,
        url=public_url,
    )
    return response.model_dump(mode="json"), 201


@openapi_route(
    summary="Update survey link",
    request_model=UpdatePublicLinkRequest,
    response_model=PublicLinkResponses,
    tags=["Survey Links"],
)
@projects_bp.route(f"{_LBASE}/<bint:link_id>", methods=["PATCH"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.edit)
def update_public_link(project_id: int, survey_id: int, link_id: int):
    payload = parse(UpdatePublicLinkRequest, request)
    updated_link = survey_link_service.update_link(
        db=get_core_db(),
        survey_id=survey_id,
        project_id=project_id,
        link_id=link_id,
        payload=payload,
        actor=g.actor,
    )
    return PublicLinkResponses.model_validate(updated_link).model_dump(mode="json"), 200


@openapi_route(summary="Delete survey link", tags=["Survey Links"], status_code=204)
@projects_bp.route(f"{_LBASE}/<bint:link_id>", methods=["DELETE"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.edit)
def delete_public_link(project_id: int, survey_id: int, link_id: int):
    survey_link_service.delete_link(
        db=get_core_db(), survey_id=survey_id, project_id=project_id, link_id=link_id, actor=g.actor
    )
    return "", 204
