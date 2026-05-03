from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from app.core.errors import AuthError
from app.schema.api.requests.auth import BootstrapUserRequest
from app.schema.orm.core.project import Project
from app.schema.orm.core.user import User
from app.services.auth import AuthService


def _make_user(sub: str = "auth0|u1", email: str = "u1@example.com", public_id: str = "abcd1234") -> User:
    user = User(auth0_user_id=sub, email=email, display_name="Test User")
    user.id = 7
    user.public_id = public_id
    return user


def _make_project(user_id: int, public_id: str) -> Project:
    project = Project(name="My Project", slug=public_id, created_by_user_id=user_id)
    project.id = 1
    return project


def _patch_verify(monkeypatch: pytest.MonkeyPatch, sub: str, email: str, name: str) -> None:
    from app.services import auth as m
    monkeypatch.setattr(m.auth, "verify_id_token", lambda _: {"sub": sub, "email": email, "name": name})


def test_bootstrap_new_user_creates_default_project(monkeypatch: pytest.MonkeyPatch) -> None:
    """bootstrap_current_user creates a default project for a new user."""
    user = _make_user()
    project = _make_project(user.id, user.public_id)

    user_service = Mock()
    user_service.bootstrap_user.return_value = (user, True)

    _patch_verify(monkeypatch, "auth0|u1", "u1@example.com", "Test User")

    db = Mock()
    db.scalar.return_value = None

    with patch("app.services.auth.projects_repo.create_project", return_value=project) as mock_create, \
         patch("app.services.auth.commit_or_rollback"):
        service = AuthService(user_service=user_service)
        result = service.bootstrap_current_user(
            db,
            access_token_sub="auth0|u1",
            payload=BootstrapUserRequest(id_token="raw-token"),
        )

    assert result.created is True
    assert result.default_project is project
    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args

    assert call_kwargs.kwargs["created_by_user_id"] == user.id
    request_arg = call_kwargs.args[1]
    assert request_arg.slug == user.public_id.lower()


def test_bootstrap_existing_user_skips_default_project(monkeypatch: pytest.MonkeyPatch) -> None:
    """bootstrap_current_user does not create a project for a returning user."""
    existing_user = _make_user()

    user_service = Mock()
    db = Mock()
    db.scalar.return_value = existing_user  # user already exists

    with patch("app.services.auth.projects_repo.create_project") as mock_create:
        service = AuthService(user_service=user_service)
        result = service.bootstrap_current_user(
            db,
            access_token_sub="auth0|u1",
            payload=BootstrapUserRequest(id_token="raw-token"),
        )

    assert result.created is False
    assert result.default_project is None
    mock_create.assert_not_called()
    user_service.bootstrap_user.assert_not_called()


def test_bootstrap_current_user_rejects_subject_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """bootstrap_current_user raises when the ID token subject does not match the access token."""
    user_service = Mock()
    service = AuthService(user_service=user_service)

    _patch_verify(monkeypatch, sub="auth0|id-token", email="u@example.com", name="U")

    db = Mock()
    db.scalar.return_value = None

    with pytest.raises(AuthError) as exc_info:
        service.bootstrap_current_user(
            db,
            access_token_sub="auth0|access-token",
            payload=BootstrapUserRequest(id_token="raw-token"),
        )

    assert exc_info.value.code == "TOKEN_SUBJECT_MISMATCH"
    user_service.bootstrap_user.assert_not_called()


def test_bootstrap_new_user_default_project_uses_public_id_as_slug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The default project slug is the user's public_id."""
    user = _make_user(public_id="xyz98765")
    project = _make_project(user.id, user.public_id)

    user_service = Mock()
    user_service.bootstrap_user.return_value = (user, True)

    _patch_verify(monkeypatch, "auth0|u1", "u1@example.com", "Test User")

    db = Mock()
    db.scalar.return_value = None

    with patch("app.services.auth.projects_repo.create_project", return_value=project), \
         patch("app.services.auth.commit_or_rollback"):
        service = AuthService(user_service=user_service)
        result = service.bootstrap_current_user(
            db,
            access_token_sub="auth0|u1",
            payload=BootstrapUserRequest(id_token="raw-token"),
        )

    assert result.default_project is not None
    assert result.default_project.slug == "xyz98765"  # already lowercase in this test
