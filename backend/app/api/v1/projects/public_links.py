from flask import request

from app.api.utils.validation import parse
from app.api.v1.projects import projects_bp, survey_link_service, users_service
from app.core.extensions import auth
from app.db.context import get_core_db
from app.openapi import openapi_route
from app.schema.api.requests.public_links import CreatePublicLinkRequest, UpdatePublicLinkRequest
from app.schema.api.responses.public_links import CreatePublicLinkOut, ListPublicLinksOut, PublicLinkOut
from app.schema.orm.core.user import User

_LBASE = "/<bint:project_id>/surveys/<bint:survey_id>/links"


@openapi_route(summary="List survey links", response_model=ListPublicLinksOut, tags=["Survey Links"])
@projects_bp.route(_LBASE, methods=["GET"])
@auth.require_auth()
def list_public_links(project_id: int, survey_id: int):
    db = get_core_db()
    user = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    links = survey_link_service.list_links(db=db, project_id=project_id, survey_id=survey_id, actor=user)
    return ListPublicLinksOut(links=[PublicLinkOut.model_validate(link) for link in links]).model_dump(mode="json"), 200


@openapi_route(
    summary="Create survey link",
    request_model=CreatePublicLinkRequest,
    response_model=CreatePublicLinkOut,
    status_code=201,
    tags=["Survey Links"],
)
@projects_bp.route(_LBASE, methods=["POST"])
@auth.require_auth()
def create_public_link(project_id: int, survey_id: int):
    payload = parse(CreatePublicLinkRequest, request)
    db = get_core_db()
    user = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())

    result = survey_link_service.create_link(
        db=db,
        survey_id=survey_id,
        project_id=project_id,
        data=payload,
        actor=user,
    )
    public_url = f"http://localhost:5173/quiz/resolve?token={result.token}"  # todo: construct URL based on config
    response = CreatePublicLinkOut(
        link=PublicLinkOut.model_validate(result.link),
        token=result.token,
        url=public_url,
    )
    return response.model_dump(mode="json"), 201


@openapi_route(
    summary="Update survey link",
    request_model=UpdatePublicLinkRequest,
    response_model=PublicLinkOut,
    tags=["Survey Links"],
)
@projects_bp.route(f"{_LBASE}/<bint:link_id>", methods=["PATCH"])
@auth.require_auth()
def update_public_link(project_id: int, survey_id: int, link_id: int):
    payload = parse(UpdatePublicLinkRequest, request)
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    updated_link = survey_link_service.update_link(
        db=db,
        survey_id=survey_id,
        project_id=project_id,
        link_id=link_id,
        payload=payload,
        actor=user,
    )
    return PublicLinkOut.model_validate(updated_link).model_dump(mode="json"), 200


@openapi_route(summary="Delete survey link", tags=["Survey Links"], status_code=204)
@projects_bp.route(f"{_LBASE}/<bint:link_id>", methods=["DELETE"])
@auth.require_auth()
def delete_public_link(project_id: int, survey_id: int, link_id: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    survey_link_service.delete_link(db=db, survey_id=survey_id, project_id=project_id, link_id=link_id, actor=user)
    return "", 204
