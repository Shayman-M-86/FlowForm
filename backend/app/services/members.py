from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.error_handling import commit_with_err_handle
from app.domain.errors import (
    AlreadyAMemberError,
    InvitationNotFoundError,
    InvitationNotPendingError,
    MemberNotFoundError,
    MemberOwnerProtectedError,
    MemberSelfActionError,
)
from app.domain.permissions import PERMISSIONS
from app.repositories import invitations_repo, members_repo, users_repo
from app.schema.api.requests.projects import SendInvitationRequest, UpdateMemberRequest
from app.schema.orm.core.invitation import ProjectInvitation
from app.schema.orm.core.project import ProjectMembership
from app.schema.orm.core.user import User
from app.services.access.access_service import require_project_permission


class MembersService:
    """Service for project member and invitation management."""

    @require_project_permission(PERMISSIONS.project.manage_members)
    def list_project_members(
        self, db: Session, *, project_id: int, actor: User  # noqa: ARG002
    ) -> list[ProjectMembership]:
        return members_repo.list_by_project(db, project_id)

    @require_project_permission(PERMISSIONS.project.manage_members)
    def list_project_invitations(
        self, db: Session, *, project_id: int, actor: User  # noqa: ARG002
    ) -> list[ProjectInvitation]:
        return invitations_repo.list_pending_by_project(db, project_id)

    @require_project_permission(PERMISSIONS.project.manage_members)
    def send_invitation(
        self,
        db: Session,
        *,
        project_id: int,
        data: SendInvitationRequest,
        actor: User,
    ) -> ProjectInvitation:
        # If the email belongs to an existing user, check they are not already a member.
        existing_user = users_repo.get_user_by_email(db, data.email)
        if existing_user is not None:
            existing_membership = members_repo.get_by_user_and_project(
                db, user_id=existing_user.id, project_id=project_id
            )
            if existing_membership is not None:
                raise AlreadyAMemberError()

        invitation = invitations_repo.create_invitation(
            db,
            project_id=project_id,
            invited_email=data.email,
            role_id=data.role_id,
            invited_by_user_id=actor.id,
            invite_message=data.invite_message,
        )
        # UNIQUE (project_id, invited_email) catches a duplicate pending invite at the DB level.
        # The integrity rule translates that to InvitationAlreadyExistsError (409).
        commit_with_err_handle(db)
        return invitation

    @require_project_permission(PERMISSIONS.project.manage_members)
    def revoke_invitation(
        self, db: Session, *, project_id: int, invitation_id: int, actor: User
    ) -> None:
        invitation = invitations_repo.get_by_id(db, invitation_id)
        if invitation is None or invitation.project_id != project_id:
            raise InvitationNotFoundError()
        if invitation.status != "pending":
            raise InvitationNotPendingError()
        invitations_repo.update_status(db, invitation, status="revoked")
        commit_with_err_handle(db)

    def get_my_invitations(self, db: Session, *, actor: User) -> list[ProjectInvitation]:
        return invitations_repo.get_pending_by_email(db, email=actor.email)

    def accept_invitation(
        self, db: Session, *, invitation_id: int, actor: User
    ) -> ProjectMembership:
        invitation = invitations_repo.get_by_id(db, invitation_id)
        if invitation is None or invitation.invited_email != actor.email:
            raise InvitationNotFoundError()
        if invitation.status != "pending":
            raise InvitationNotPendingError()

        existing = members_repo.get_by_user_and_project(
            db, user_id=actor.id, project_id=invitation.project_id
        )
        if existing is not None:
            raise AlreadyAMemberError()

        membership = members_repo.create_membership(
            db,
            project_id=invitation.project_id,
            user_id=actor.id,
            role_id=invitation.role_id,
        )
        invitations_repo.update_status(
            db,
            invitation,
            status="accepted",
            accepted_by_user_id=actor.id,
            accepted_at=datetime.now(UTC),
        )
        commit_with_err_handle(db)
        return membership

    def decline_invitation(
        self, db: Session, *, invitation_id: int, actor: User
    ) -> None:
        invitation = invitations_repo.get_by_id(db, invitation_id)
        if invitation is None or invitation.invited_email != actor.email:
            raise InvitationNotFoundError()
        if invitation.status != "pending":
            raise InvitationNotPendingError()
        invitations_repo.update_status(db, invitation, status="declined")
        commit_with_err_handle(db)

    def _get_member(self, db: Session, *, membership_id: int, project_id: int) -> ProjectMembership:
        membership = members_repo.get_by_id(db, membership_id=membership_id, project_id=project_id)
        if membership is None:
            raise MemberNotFoundError()
        return membership

    @require_project_permission(PERMISSIONS.project.manage_members)
    def remove_member(
        self, db: Session, *, project_id: int, membership_id: int, actor: User
    ) -> None:
        membership = self._get_member(db, membership_id=membership_id, project_id=project_id)
        if membership.user_id == actor.id:
            raise MemberSelfActionError()
        if membership.role is not None and membership.role.is_system_role:
            raise MemberOwnerProtectedError()
        members_repo.delete_membership(db, membership)
        commit_with_err_handle(db)

    @require_project_permission(PERMISSIONS.project.manage_members)
    def update_member(
        self, db: Session, *, project_id: int, membership_id: int, data: UpdateMemberRequest, actor: User
    ) -> ProjectMembership:
        membership = self._get_member(db, membership_id=membership_id, project_id=project_id)
        if membership.user_id == actor.id:
            raise MemberSelfActionError()
        # Guard suspend/role-strip on system-role members
        suspending = "status" in data.model_fields_set and data.status == "suspended"
        clearing_role = "role_id" in data.model_fields_set and data.role_id is None
        if (suspending or clearing_role) and membership.role is not None and membership.role.is_system_role:
            raise MemberOwnerProtectedError()
        updated = members_repo.update_membership(
            db,
            membership,
            fields_set=data.model_fields_set,
            role_id=data.role_id,
            status=data.status,
        )
        commit_with_err_handle(db)
        return updated


members_service = MembersService()
