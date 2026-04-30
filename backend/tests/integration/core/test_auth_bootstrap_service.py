from __future__ import annotations

from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session, scoped_session

from app.schema.api.requests.auth import BootstrapUserRequest
from app.schema.orm.core.project import Project, ProjectMembership
from app.schema.orm.core.user import User
from app.services.auth import AuthService
from tests.integration.core.factories import make_user


def _make_auth_service(db: Session, monkeypatch: pytest.MonkeyPatch, *, sub: str, email: str, name: str) -> AuthService:
    """Return an AuthService with verify_id_token monkeypatched."""
    from app.services import auth as auth_module
    monkeypatch.setattr(
        auth_module.auth,
        "verify_id_token",
        lambda _: {"sub": sub, "email": email, "name": name},
    )
    return AuthService()


def test_bootstrap_new_user_creates_default_project(
    db_session: scoped_session[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A new user gets a default project created during bootstrap."""
    service = _make_auth_service(
        db_session,  # type: ignore
        monkeypatch,
        sub="auth0|boot-proj-new",
        email="boot-proj-new@example.com",
        name="New User",
    )

    result = service.bootstrap_current_user(
        db_session,  # type: ignore
        access_token_sub="auth0|boot-proj-new",
        payload=BootstrapUserRequest(id_token="raw-token"),
    )

    assert result.created is True
    assert result.default_project is not None
    assert result.default_project.slug == result.user.public_id.lower()
    assert result.default_project.created_by_user_id == result.user.id

    project = db_session.get(Project, result.default_project.id)
    assert project is not None


def test_bootstrap_new_user_default_project_has_owner_membership(
    db_session: scoped_session[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The default project has an Owner membership for the new user."""
    from sqlalchemy import select

    service = _make_auth_service(
        db_session,  # type: ignore
        monkeypatch,
        sub="auth0|boot-proj-member",
        email="boot-proj-member@example.com",
        name="Member User",
    )

    result = service.bootstrap_current_user(
        db_session,  # type: ignore
        access_token_sub="auth0|boot-proj-member",
        payload=BootstrapUserRequest(id_token="raw-token"),
    )

    assert result.default_project is not None
    membership = db_session.scalar(
        select(ProjectMembership).where(
            ProjectMembership.project_id == result.default_project.id,
            ProjectMembership.user_id == result.user.id,
        )
    )
    assert membership is not None


def test_bootstrap_existing_user_does_not_create_project(
    db_session: scoped_session[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returning users do not get a new default project on re-bootstrap."""
    existing = make_user(auth0_user_id="auth0|boot-proj-existing", email="boot-proj-existing@example.com")
    db_session.add(existing)
    db_session.commit()  # type: ignore

    service = _make_auth_service(
        db_session,  # type: ignore
        monkeypatch,
        sub="auth0|boot-proj-existing",
        email="boot-proj-existing@example.com",
        name="Existing User",
    )

    result = service.bootstrap_current_user(
        db_session,  # type: ignore
        access_token_sub="auth0|boot-proj-existing",
        payload=BootstrapUserRequest(id_token="raw-token"),
    )

    assert result.created is False
    assert result.default_project is None


def test_bootstrap_new_user_default_project_slug_is_public_id(
    db_session: scoped_session[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The default project slug equals the user's public_id, ensuring uniqueness."""
    service = _make_auth_service(
        db_session,  # type: ignore
        monkeypatch,
        sub="auth0|boot-proj-slug",
        email="boot-proj-slug@example.com",
        name="Slug User",
    )

    result = service.bootstrap_current_user(
        db_session,  # type: ignore
        access_token_sub="auth0|boot-proj-slug",
        payload=BootstrapUserRequest(id_token="raw-token"),
    )

    assert result.default_project is not None
    assert result.default_project.slug == result.user.public_id.lower()
    assert len(result.default_project.slug) == 8

