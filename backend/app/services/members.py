from datetime import UTC, datetime  # noqa: I001

from sqlalchemy.orm import Session

from app.core.config import current_settings
from app.db.error_handling import commit_with_err_handle
from app.email_service import get_email_service
from app.domain.errors import (
    AlreadyAMemberError,
    InvitationNotFoundError,
    InvitationNotPendingError,
    MemberNotFoundError,
    MemberOwnerProtectedError,
    MemberSelfActionError,
    ProjectRoleNotFoundError,
)
from app.domain.guards import ensure_present
from app.repositories import (
    invitations_repo as ir,
    members_repo as mr,
    roles_repo as rr,
    users_repo as ur,
)
from app.schema.api.requests.projects import SendInvitationRequest, UpdateMemberRequest
from app.schema.orm.core.invitation import ProjectInvitation
from app.schema.orm.core.project import ProjectMembership, ProjectRole
from app.schema.orm.core.user import User


class MembersService:
    """Service for project member and invitation management."""

    def _get_assignable_role(self, db: Session, *, project_id: int, role_id: int | None) -> ProjectRole | None:
        if role_id is None:
            return None
        role = ensure_present(
            rr.get_by_id(db, role_id=role_id, project_id=project_id),
            error=ProjectRoleNotFoundError(),
        )
        if role.is_system_role:
            raise MemberOwnerProtectedError()
        return role

    def list_project_members(
        self,
        db: Session,
        *,
        project_id: int,
        actor: User,  # noqa: ARG002
    ) -> list[ProjectMembership]:
        return mr.list_by_project(db, project_id)

    def list_project_invitations(
        self,
        db: Session,
        *,
        project_id: int,
        actor: User,  # noqa: ARG002
    ) -> list[ProjectInvitation]:
        return ir.list_pending_by_project(db, project_id)

    def send_invitation(
        self,
        db: Session,
        *,
        project_id: int,
        data: SendInvitationRequest,
        actor: User,
    ) -> ProjectInvitation:
        # If the email belongs to an existing user, check they are not already a member.
        existing_user = ur.get_user_by_email(db, data.email)
        if existing_user is not None:
            existing_membership = mr.get_by_user_and_project(db, user_id=existing_user.id, project_id=project_id)
            if existing_membership is not None:
                raise AlreadyAMemberError()
        self._get_assignable_role(db, project_id=project_id, role_id=data.role_id)

        invitation, token = ir.create_invitation(
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

        get_email_service().send_project_member_invite({
            "to_email": data.email,
            "inviter_name": actor.display_name,
            "project_name": invitation.project.name,
            "invite_url": f"{current_settings().flowform.server.site_url.rstrip('/')}/invitations/{token}",
        })

        return invitation

    def revoke_invitation(
        self,
        db: Session,
        *,
        project_id: int,
        invitation_id: int,
        actor: User,  # noqa: ARG002
    ) -> None:
        invitation = ensure_present(
            ir.get_by_id(db, invitation_id),
            error=InvitationNotFoundError(),
        )
        if invitation.project_id != project_id:
            raise InvitationNotFoundError()
        if invitation.status != "pending":
            raise InvitationNotPendingError()
        ir.update_status(db, invitation, status="revoked")
        commit_with_err_handle(db)

    def get_my_invitations(self, db: Session, *, actor: User) -> list[ProjectInvitation]:
        return ir.get_pending_by_email(db, email=actor.email)

    def accept_invitation(self, db: Session, *, invitation_id: int, actor: User) -> ProjectMembership:
        invitation = ensure_present(
            ir.get_by_id(db, invitation_id),
            error=InvitationNotFoundError(),
        )
        if invitation.invited_email != actor.email:
            raise InvitationNotFoundError()
        if invitation.status != "pending":
            raise InvitationNotPendingError()

        existing = mr.get_by_user_and_project(db, user_id=actor.id, project_id=invitation.project_id)
        if existing is not None:
            raise AlreadyAMemberError()
        self._get_assignable_role(db, project_id=invitation.project_id, role_id=invitation.role_id)

        membership = mr.create_membership(
            db,
            project_id=invitation.project_id,
            user_id=actor.id,
            role_id=invitation.role_id,
        )
        ir.update_status(
            db,
            invitation,
            status="accepted",
            accepted_by_user_id=actor.id,
            accepted_at=datetime.now(UTC),
        )
        commit_with_err_handle(db)
        return membership

    def decline_invitation(self, db: Session, *, invitation_id: int, actor: User) -> None:
        invitation = ensure_present(
            ir.get_by_id(db, invitation_id),
            error=InvitationNotFoundError(),
        )
        if invitation.invited_email != actor.email:
            raise InvitationNotFoundError()
        if invitation.status != "pending":
            raise InvitationNotPendingError()
        ir.update_status(db, invitation, status="declined")
        commit_with_err_handle(db)

    def resolve_invitation_by_token(self, db: Session, *, token: str) -> ProjectInvitation:
        """Look up an invitation by its raw token for public resolution."""
        invitation = ensure_present(
            ir.get_by_token(db, token),
            error=InvitationNotFoundError(),
        )
        return invitation

    def _get_member(self, db: Session, *, membership_id: int, project_id: int) -> ProjectMembership:
        return ensure_present(
            mr.get_by_id(db, membership_id=membership_id, project_id=project_id),
            error=MemberNotFoundError(),
        )

    def remove_member(self, db: Session, *, project_id: int, membership_id: int, actor: User) -> None:
        membership = self._get_member(db, membership_id=membership_id, project_id=project_id)
        if membership.user_id == actor.id:
            raise MemberSelfActionError()
        if membership.role is not None and membership.role.is_system_role:
            raise MemberOwnerProtectedError()
        mr.delete_membership(db, membership)
        commit_with_err_handle(db)

    def update_member(
        self, db: Session, *, project_id: int, membership_id: int, data: UpdateMemberRequest, actor: User
    ) -> ProjectMembership:
        membership = self._get_member(db, membership_id=membership_id, project_id=project_id)
        if membership.user_id == actor.id:
            raise MemberSelfActionError()
        role_changed = "role_id" in data.model_fields_set and data.role_id != membership.role_id
        suspending = "status" in data.model_fields_set and data.status == "suspended"
        clearing_role = "role_id" in data.model_fields_set and data.role_id is None
        if (
            (role_changed or suspending or clearing_role)
            and membership.role is not None
            and membership.role.is_system_role
        ):
            raise MemberOwnerProtectedError()
        if role_changed:
            self._get_assignable_role(db, project_id=project_id, role_id=data.role_id)
        updated = mr.update_membership(
            db,
            membership,
            fields_set=data.model_fields_set,
            role_id=data.role_id,
            status=data.status,
        )
        commit_with_err_handle(db)
        return updated


members_service = MembersService()
