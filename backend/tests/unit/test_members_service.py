from __future__ import annotations

from unittest.mock import Mock

import pytest

from app.domain.errors import MemberOwnerProtectedError
from app.schema.api.requests.projects import SendInvitationRequest, UpdateMemberRequest
from app.schema.orm.core.invitation import ProjectInvitation
from app.schema.orm.core.project import ProjectMembership, ProjectRole
from app.schema.orm.core.user import User
from app.services import members as members_module
from app.services.members import MembersService


def _actor() -> User:
    user = User()
    user.id = 1
    user.email = "actor@example.com"
    user.platform_admin = True
    return user


def _role(*, role_id: int, project_id: int = 10, is_system_role: bool) -> ProjectRole:
    role = ProjectRole()
    role.id = role_id
    role.project_id = project_id
    role.name = "Owner" if is_system_role else "Editor"
    role.is_system_role = is_system_role
    return role


def _membership(*, role: ProjectRole, user_id: int = 2, project_id: int = 10) -> ProjectMembership:
    membership = ProjectMembership()
    membership.id = 20
    membership.user_id = user_id
    membership.project_id = project_id
    membership.role_id = role.id
    membership.role = role
    return membership


def _invitation(*, role_id: int, project_id: int = 10) -> ProjectInvitation:
    invitation = ProjectInvitation()
    invitation.id = 30
    invitation.project_id = project_id
    invitation.invited_email = "invitee@example.com"
    invitation.status = "pending"
    invitation.role_id = role_id
    return invitation


def test_send_invitation_rejects_system_role(monkeypatch: pytest.MonkeyPatch) -> None:
    service = MembersService()
    owner_role = _role(role_id=1, is_system_role=True)
    create_invitation = Mock()

    monkeypatch.setattr(members_module.users_repo, "get_user_by_email", Mock(return_value=None))
    monkeypatch.setattr(members_module.roles_repo, "get_by_id", Mock(return_value=owner_role))
    monkeypatch.setattr(members_module.invitations_repo, "create_invitation", create_invitation)

    with pytest.raises(MemberOwnerProtectedError):
        service.send_invitation(
            Mock(),
            project_id=10,
            data=SendInvitationRequest(email="invitee@example.com", role_id=owner_role.id),
            actor=_actor(),
        )

    create_invitation.assert_not_called()


def test_update_member_rejects_changing_owner_to_another_role(monkeypatch: pytest.MonkeyPatch) -> None:
    service = MembersService()
    owner_membership = _membership(role=_role(role_id=1, is_system_role=True))
    update_membership = Mock()

    monkeypatch.setattr(members_module.members_repo, "get_by_id", Mock(return_value=owner_membership))
    monkeypatch.setattr(members_module.members_repo, "update_membership", update_membership)

    with pytest.raises(MemberOwnerProtectedError):
        service.update_member(
            Mock(),
            project_id=10,
            membership_id=owner_membership.id,
            data=UpdateMemberRequest(role_id=2),
            actor=_actor(),
        )

    update_membership.assert_not_called()


def test_update_member_rejects_assigning_system_role(monkeypatch: pytest.MonkeyPatch) -> None:
    service = MembersService()
    current_membership = _membership(role=_role(role_id=2, is_system_role=False))
    owner_role = _role(role_id=1, is_system_role=True)
    update_membership = Mock()

    monkeypatch.setattr(members_module.members_repo, "get_by_id", Mock(return_value=current_membership))
    monkeypatch.setattr(members_module.roles_repo, "get_by_id", Mock(return_value=owner_role))
    monkeypatch.setattr(members_module.members_repo, "update_membership", update_membership)

    with pytest.raises(MemberOwnerProtectedError):
        service.update_member(
            Mock(),
            project_id=10,
            membership_id=current_membership.id,
            data=UpdateMemberRequest(role_id=owner_role.id),
            actor=_actor(),
        )

    update_membership.assert_not_called()


def test_accept_invitation_rejects_system_role(monkeypatch: pytest.MonkeyPatch) -> None:
    service = MembersService()
    invitation = _invitation(role_id=1)
    owner_role = _role(role_id=1, is_system_role=True)
    create_membership = Mock()
    invitee = _actor()
    invitee.id = 2
    invitee.email = invitation.invited_email

    monkeypatch.setattr(members_module.invitations_repo, "get_by_id", Mock(return_value=invitation))
    monkeypatch.setattr(members_module.members_repo, "get_by_user_and_project", Mock(return_value=None))
    monkeypatch.setattr(members_module.roles_repo, "get_by_id", Mock(return_value=owner_role))
    monkeypatch.setattr(members_module.members_repo, "create_membership", create_membership)

    with pytest.raises(MemberOwnerProtectedError):
        service.accept_invitation(Mock(), invitation_id=invitation.id, actor=invitee)

    create_membership.assert_not_called()
