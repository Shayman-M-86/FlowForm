from uuid import UUID

from flask import request

from app.api.utils.validation import parse
from app.api.v1.studio.projects import participant_service, studio_projects_bp
from app.core.extensions import auth
from app.db.context import get_core_db
from app.domain.permissions import PERMISSIONS
from app.openapi import openapi_route
from app.schema.api.requests.participants import CreateParticipantRequest, UpdateParticipantRequest
from app.schema.api.responses.participants import ListParticipantsResponses, ParticipantResponses
from app.services.access.access_service import require_project_permission

_BASE = "/<bint:project_id>/participants"


@openapi_route(summary="List participants", response_model=ListParticipantsResponses, tags=["Participants"])
@studio_projects_bp.route(_BASE, methods=["GET"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_members)
def list_participants(project_id: int):
    participants = participant_service.list_participants(db=get_core_db(), project_id=project_id)
    return ListParticipantsResponses(
        participants=[ParticipantResponses.model_validate(p) for p in participants]
    ).model_dump(mode="json"), 200


@openapi_route(
    summary="Create participant",
    request_model=CreateParticipantRequest,
    response_model=ParticipantResponses,
    status_code=201,
    tags=["Participants"],
)
@studio_projects_bp.route(_BASE, methods=["POST"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_members)
def create_participant(project_id: int):
    payload = parse(CreateParticipantRequest, request)
    participant = participant_service.create_participant(db=get_core_db(), project_id=project_id, data=payload)
    return ParticipantResponses.model_validate(participant).model_dump(mode="json"), 201


@openapi_route(
    summary="Update participant",
    request_model=UpdateParticipantRequest,
    response_model=ParticipantResponses,
    tags=["Participants"],
)
@studio_projects_bp.route(f"{_BASE}/<uuid:participant_id>", methods=["PATCH"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_members)
def update_participant(project_id: int, participant_id: UUID):
    payload = parse(UpdateParticipantRequest, request)
    participant = participant_service.update_participant(
        db=get_core_db(), project_id=project_id, participant_id=participant_id, data=payload
    )
    return ParticipantResponses.model_validate(participant).model_dump(mode="json"), 200


@openapi_route(summary="Delete participant", tags=["Participants"], status_code=204)
@studio_projects_bp.route(f"{_BASE}/<uuid:participant_id>", methods=["DELETE"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_members)
def delete_participant(project_id: int, participant_id: UUID):
    participant_service.delete_participant(db=get_core_db(), project_id=project_id, participant_id=participant_id)
    return {}, 204
