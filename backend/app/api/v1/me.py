from flask import Blueprint

from app.api.utils.validation import parse
from app.core.extensions import auth
from app.db.context import get_core_db
from app.openapi import openapi_route
from app.schema.api.responses.projects import ProjectInvitationOut, ProjectMemberOut
from app.schema.orm.core.user import User
from app.services.members import members_service
from app.services.users import UserService

me_bp = Blueprint("me_v1", __name__)

_users_service = UserService()


@openapi_route(
    summary="Get my invitations",
    response_model=list[ProjectInvitationOut],
    tags=["Me"],
)
@me_bp.route("/invitations", methods=["GET"])
@auth.require_auth()
def get_my_invitations():
    db = get_core_db()
    actor: User = _users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    invitations = members_service.get_my_invitations(db=db, actor=actor)
    return [ProjectInvitationOut.from_orm_with_project(i).model_dump(mode="json") for i in invitations], 200


@openapi_route(
    summary="Accept invitation",
    response_model=ProjectMemberOut,
    status_code=200,
    tags=["Me"],
)
@me_bp.route("/invitations/<bint:invitation_id>/accept", methods=["POST"])
@auth.require_auth()
def accept_invitation(invitation_id: int):
    db = get_core_db()
    actor: User = _users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    membership = members_service.accept_invitation(db=db, invitation_id=invitation_id, actor=actor)
    return ProjectMemberOut.model_validate(membership).model_dump(mode="json"), 200


@openapi_route(
    summary="Decline invitation",
    tags=["Me"],
)
@me_bp.route("/invitations/<bint:invitation_id>/decline", methods=["POST"])
@auth.require_auth()
def decline_invitation(invitation_id: int):
    db = get_core_db()
    actor: User = _users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    members_service.decline_invitation(db=db, invitation_id=invitation_id, actor=actor)
    return {}, 204
