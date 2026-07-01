from __future__ import annotations

from unittest.mock import Mock

import pytest

from app.core.extensions import auth
from app.domain.errors import EmailNotVerifiedError, InvitationNotFoundError, MemberOwnerProtectedError
from app.middleware.auth.auth0 import ManagementApiError
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
    user.email_verified = True
    user.auth0_user_id = "auth0|actor"
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
    invitation.token_hash = "fakehash"
    return invitation


def test_send_invitation_rejects_system_role(monkeypatch: pytest.MonkeyPatch) -> None:
    service = MembersService()
    owner_role = _role(role_id=1, is_system_role=True)
    create_invitation = Mock()

    monkeypatch.setattr(members_module.ur, "get_user_by_email", Mock(return_value=None))
    monkeypatch.setattr(members_module.rr, "get_by_id", Mock(return_value=owner_role))
    monkeypatch.setattr(members_module.ir, "create_invitation", create_invitation)

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

    monkeypatch.setattr(members_module.mr, "get_by_id", Mock(return_value=owner_membership))
    monkeypatch.setattr(members_module.mr, "update_membership", update_membership)

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

    monkeypatch.setattr(members_module.mr, "get_by_id", Mock(return_value=current_membership))
    monkeypatch.setattr(members_module.rr, "get_by_id", Mock(return_value=owner_role))
    monkeypatch.setattr(members_module.mr, "update_membership", update_membership)

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

    monkeypatch.setattr(members_module.ir, "get_by_id", Mock(return_value=invitation))
    monkeypatch.setattr(members_module.mr, "get_by_user_and_project", Mock(return_value=None))
    monkeypatch.setattr(members_module.rr, "get_by_id", Mock(return_value=owner_role))
    monkeypatch.setattr(members_module.mr, "create_membership", create_membership)

    with pytest.raises(MemberOwnerProtectedError):
        service.accept_invitation(Mock(), invitation_id=invitation.id, actor=invitee)

    create_membership.assert_not_called()


def test_accept_invitation_rejects_unverified_actor_when_mgmt_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = MembersService()
    invitation = _invitation(role_id=1)
    invitee = _actor()
    invitee.id = 2
    invitee.email = invitation.invited_email
    invitee.email_verified = False

    monkeypatch.setattr(members_module.ir, "get_by_id", Mock(return_value=invitation))

    with pytest.raises(EmailNotVerifiedError):
        service.accept_invitation(Mock(), invitation_id=invitation.id, actor=invitee)


def test_accept_invitation_rejects_unverified_actor_when_live_check_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mgmt = Mock()
    mgmt.get_user_email_verified = Mock(return_value=False)
    monkeypatch.setattr(auth, "mgmt", mgmt)
    service = MembersService()
    invitation = _invitation(role_id=1)
    invitee = _actor()
    invitee.id = 2
    invitee.email = invitation.invited_email
    invitee.email_verified = False

    monkeypatch.setattr(members_module.ir, "get_by_id", Mock(return_value=invitation))

    with pytest.raises(EmailNotVerifiedError):
        service.accept_invitation(Mock(), invitation_id=invitation.id, actor=invitee)

    mgmt.get_user_email_verified.assert_called_once_with(invitee.auth0_user_id)


def test_accept_invitation_succeeds_via_lazy_auth0_check(monkeypatch: pytest.MonkeyPatch) -> None:
    mgmt = Mock()
    mgmt.get_user_email_verified = Mock(return_value=True)
    monkeypatch.setattr(auth, "mgmt", mgmt)
    service = MembersService()
    role = _role(role_id=1, is_system_role=False)
    invitation = _invitation(role_id=1)
    invitee = _actor()
    invitee.id = 2
    invitee.email = invitation.invited_email
    invitee.email_verified = False
    create_membership = Mock(return_value=Mock())

    monkeypatch.setattr(members_module.ir, "get_by_id", Mock(return_value=invitation))
    monkeypatch.setattr(members_module.mr, "get_by_user_and_project", Mock(return_value=None))
    monkeypatch.setattr(members_module.rr, "get_by_id", Mock(return_value=role))
    monkeypatch.setattr(members_module.mr, "create_membership", create_membership)
    monkeypatch.setattr(members_module.ir, "update_status", Mock())
    monkeypatch.setattr(members_module, "commit_with_err_handle", Mock())
    set_email_verified = Mock()
    monkeypatch.setattr(members_module.ur, "set_email_verified", set_email_verified)

    membership = service.accept_invitation(Mock(), invitation_id=invitation.id, actor=invitee)

    assert membership is create_membership.return_value
    set_email_verified.assert_called_once_with(invitee, email_verified=True)
    create_membership.assert_called_once()


def test_accept_invitation_skips_live_check_when_already_verified(monkeypatch: pytest.MonkeyPatch) -> None:
    service = MembersService()
    role = _role(role_id=1, is_system_role=False)
    invitation = _invitation(role_id=1)
    invitee = _actor()
    invitee.id = 2
    invitee.email = invitation.invited_email
    invitee.email_verified = True
    create_membership = Mock(return_value=Mock())

    monkeypatch.setattr(members_module.ir, "get_by_id", Mock(return_value=invitation))
    monkeypatch.setattr(members_module.mr, "get_by_user_and_project", Mock(return_value=None))
    monkeypatch.setattr(members_module.rr, "get_by_id", Mock(return_value=role))
    monkeypatch.setattr(members_module.mr, "create_membership", create_membership)
    monkeypatch.setattr(members_module.ir, "update_status", Mock())
    monkeypatch.setattr(members_module, "commit_with_err_handle", Mock())

    membership = service.accept_invitation(Mock(), invitation_id=invitation.id, actor=invitee)

    assert membership is create_membership.return_value


def test_accept_invitation_by_token_succeeds_and_marks_verified(monkeypatch: pytest.MonkeyPatch) -> None:
    mgmt = Mock()
    mgmt.mark_email_verified = Mock()
    monkeypatch.setattr(auth, "mgmt", mgmt)
    service = MembersService()
    role = _role(role_id=1, is_system_role=False)
    invitation = _invitation(role_id=1)
    invitee = _actor()
    invitee.id = 2
    invitee.email = invitation.invited_email
    invitee.email_verified = False
    create_membership = Mock(return_value=Mock())

    monkeypatch.setattr(members_module.ir, "get_by_token", Mock(return_value=invitation))
    monkeypatch.setattr(members_module.mr, "get_by_user_and_project", Mock(return_value=None))
    monkeypatch.setattr(members_module.rr, "get_by_id", Mock(return_value=role))
    monkeypatch.setattr(members_module.mr, "create_membership", create_membership)
    monkeypatch.setattr(members_module.ir, "update_status", Mock())
    monkeypatch.setattr(members_module, "commit_with_err_handle", Mock())
    set_email_verified = Mock()
    monkeypatch.setattr(members_module.ur, "set_email_verified", set_email_verified)

    membership = service.accept_invitation_by_token(
        Mock(), token="raw-token", actor=invitee,
    )

    assert membership is create_membership.return_value
    set_email_verified.assert_called_once_with(invitee, email_verified=True)
    mgmt.mark_email_verified.assert_called_once_with(invitee.auth0_user_id)


def test_accept_invitation_by_token_swallows_auth0_mirror_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    mgmt = Mock()
    mgmt.mark_email_verified = Mock(
        side_effect=ManagementApiError(status_code=500, provider_error="boom", provider_message="boom"),
    )
    monkeypatch.setattr(auth, "mgmt", mgmt)
    service = MembersService()
    role = _role(role_id=1, is_system_role=False)
    invitation = _invitation(role_id=1)
    invitee = _actor()
    invitee.id = 2
    invitee.email = invitation.invited_email
    invitee.email_verified = False
    create_membership = Mock(return_value=Mock())

    monkeypatch.setattr(members_module.ir, "get_by_token", Mock(return_value=invitation))
    monkeypatch.setattr(members_module.mr, "get_by_user_and_project", Mock(return_value=None))
    monkeypatch.setattr(members_module.rr, "get_by_id", Mock(return_value=role))
    monkeypatch.setattr(members_module.mr, "create_membership", create_membership)
    monkeypatch.setattr(members_module.ir, "update_status", Mock())
    monkeypatch.setattr(members_module, "commit_with_err_handle", Mock())
    monkeypatch.setattr(members_module.ur, "set_email_verified", Mock())

    membership = service.accept_invitation_by_token(
        Mock(), token="raw-token", actor=invitee,
    )

    assert membership is create_membership.return_value


def test_accept_invitation_by_token_rejects_email_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    service = MembersService()
    invitation = _invitation(role_id=1)
    invitee = _actor()
    invitee.id = 2
    invitee.email = "someone-else@example.com"

    monkeypatch.setattr(members_module.ir, "get_by_token", Mock(return_value=invitation))

    with pytest.raises(InvitationNotFoundError):
        service.accept_invitation_by_token(Mock(), token="raw-token", actor=invitee)
