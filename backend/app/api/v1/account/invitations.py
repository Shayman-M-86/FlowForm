from app.api.v1.account import _users_service, account_bp
from app.core.extensions import auth
from app.db.context import get_core_db
from app.openapi import openapi_route
from app.schema.api.responses.projects import ProjectInvitationResponses, ProjectMemberResponses
from app.schema.orm.core.user import User
from app.services.members import members_service


@openapi_route(
    summary="Get my invitations",
    response_model=list[ProjectInvitationResponses],
    tags=["Account Invitations"],
)
@account_bp.route("/invitations", methods=["GET"])
@auth.require_auth()
def get_my_invitations():
    db = get_core_db()
    actor: User = _users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    invitations = members_service.get_my_invitations(db=db, actor=actor)
    return [ProjectInvitationResponses.from_orm_with_project(i).model_dump(mode="json") for i in invitations], 200


@openapi_route(
    summary="Accept invitation",
    response_model=ProjectMemberResponses,
    status_code=200,
    tags=["Account Invitations"],
)
@account_bp.route("/invitations/<bint:invitation_id>/accept", methods=["POST"])
@auth.require_auth()
def accept_invitation(invitation_id: int):
    db = get_core_db()
    actor: User = _users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    membership = members_service.accept_invitation(db=db, invitation_id=invitation_id, actor=actor)
    return ProjectMemberResponses.model_validate(membership).model_dump(mode="json"), 200


@openapi_route(
    summary="Decline invitation",
    tags=["Account Invitations"],
)
@account_bp.route("/invitations/<bint:invitation_id>/decline", methods=["POST"])
@auth.require_auth()
def decline_invitation(invitation_id: int):
    db = get_core_db()
    actor: User = _users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    members_service.decline_invitation(db=db, invitation_id=invitation_id, actor=actor)
    return {}, 204
