from uuid import UUID

from flask import g, request

from app.api.utils.serialization import serialize
from app.api.utils.validation import parse
from app.api.v1.studio.projects import content_svc, studio_projects_bp
from app.core.extensions import auth
from app.db.context import get_core_db
from app.domain.permissions import PERMISSIONS
from app.openapi import openapi_route
from app.schema.api.requests.content import CreateNodeRequest, UpdateNodeRequest
from app.schema.api.responses.content import NodeResponses
from app.services.access.access_service import require_survey_permission

_BASE = "/<bint:project_id>/surveys/<bint:survey_id>/versions/<bint:version_number>/nodes"


@openapi_route(summary="List survey builder nodes", response_model=list[NodeResponses], tags=["Survey Builder"])
@studio_projects_bp.route(_BASE, methods=["GET"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.view)
def list_nodes(project_id: int, survey_id: int, version_number: int):
    nodes = content_svc.list_nodes(
        db=get_core_db(), project_id=project_id, survey_id=survey_id, version_number=version_number, actor=g.actor
    )
    return [serialize(NodeResponses, n) for n in nodes], 200


@openapi_route(
    summary="Create survey builder node",
    request_model=CreateNodeRequest,
    response_model=NodeResponses,
    status_code=201,
    tags=["Survey Builder"],
)
@studio_projects_bp.route(_BASE, methods=["POST"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.edit)
def create_node(project_id: int, survey_id: int, version_number: int):
    payload = parse(CreateNodeRequest, request)
    node = content_svc.create_node(
        db=get_core_db(),
        project_id=project_id,
        survey_id=survey_id,
        version_number=version_number,
        data=payload,
        actor=g.actor,
    )
    return serialize(NodeResponses, node), 201


@openapi_route(summary="Get survey builder node", response_model=NodeResponses, tags=["Survey Builder"])
@studio_projects_bp.route(f"{_BASE}/<uuid:node_id>", methods=["GET"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.view)
def get_node(project_id: int, survey_id: int, version_number: int, node_id: UUID):
    node = content_svc.get_node(
        db=get_core_db(),
        project_id=project_id,
        survey_id=survey_id,
        version_number=version_number,
        node_id=node_id,
        actor=g.actor,
    )
    return serialize(NodeResponses, node), 200


@openapi_route(
    summary="Update survey builder node",
    request_model=UpdateNodeRequest,
    response_model=NodeResponses,
    tags=["Survey Builder"],
)
@studio_projects_bp.route(f"{_BASE}/<uuid:node_id>", methods=["PATCH"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.edit)
def update_node(project_id: int, survey_id: int, version_number: int, node_id: UUID):
    payload = parse(UpdateNodeRequest, request)
    node = content_svc.update_node(
        db=get_core_db(),
        project_id=project_id,
        survey_id=survey_id,
        version_number=version_number,
        node_id=node_id,
        data=payload,
        actor=g.actor,
    )
    return serialize(NodeResponses, node), 200


@openapi_route(summary="Delete survey builder node", tags=["Survey Builder"], status_code=204)
@studio_projects_bp.route(f"{_BASE}/<uuid:node_id>", methods=["DELETE"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.edit)
def delete_node(project_id: int, survey_id: int, version_number: int, node_id: UUID):
    content_svc.delete_node(
        db=get_core_db(),
        project_id=project_id,
        survey_id=survey_id,
        version_number=version_number,
        node_id=node_id,
        actor=g.actor,
    )
    return "", 204
