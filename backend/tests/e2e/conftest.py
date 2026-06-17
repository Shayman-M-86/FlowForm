"""End-to-end test harness.

These tests drive the full request lifecycle through Flask's test client:
HTTP route -> auth/RBAC decorators -> service -> repository -> real Postgres.
Unlike the integration tests (which hand-roll ORM inserts and inspect the DB
directly), e2e tests exercise the exact code path a real client hits, so they
catch bugs that live in the wiring *between* layers -- e.g. a route or repo
that forgets to populate a NOT NULL column.

Isolation: routes obtain their sessions from ``flask.g.core_db`` /
``flask.g.response_db``, which the app's ``before_request`` hook
(``open_request_sessions``) populates by calling
``db_manager.create_core_session()`` / ``create_response_session()``. We patch
those two factories to hand back the test's savepoint-bound sessions, so every
request inside a test shares data with the test and rolls back at teardown.

Because the request-teardown hook (``close_request_sessions``) calls
``.close()`` (and ``.rollback()`` on error) on the ``g`` sessions, we hand the
factories a thin proxy whose ``close`` / ``rollback`` are no-ops -- the
``core_db_session`` / ``response_db_session`` fixtures own the real lifecycle.
Route ``.commit()`` still runs and lands on a savepoint; the outer transaction
rolls back when the connection fixture tears down.

Auth: ``auth._verify_access_token`` is monkeypatched to return fixed claims for
a seeded user, mirroring ``tests/unit/test_auth_bootstrap_route.py``. The seeded
user is a real project member with a role granting the survey permissions the
routes require, so the survey-permission decorator runs for real. (Platform
admin can't be used here -- ``ck_users_platform_admin`` restricts it to id=1,
which we can't guarantee under savepoint isolation.) The ``permissions`` rows
themselves are seeded into the real DB at app startup by ``init_seed_data``, so
they're visible to the test connection and we just look them up by name.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any, NamedTuple

import pytest  # type: ignore[import]
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy.orm import Session

from app.core.extensions import auth, db_manager
from app.domain.permissions import PERMISSIONS
from app.repositories import permissions_repo as per
from app.schema.orm.core import (
    Project,
    ProjectMembership,
    ResponseStore,
    Survey,
    SurveyVersion,
    User,
)
from tests.integration.core.factories import (
    make_project,
    make_project_role,
    make_response_store,
    make_survey,
    make_survey_version,
    make_user,
)

_MEMBER_SUB = "auth0|e2e-member"

# Permissions the survey-link routes require (view for list, edit for
# create/update/delete).
_GRANTED_PERMISSIONS = (PERMISSIONS.survey.view, PERMISSIONS.survey.edit)


class _NonClosingSession:
    """Proxy that forwards everything to a real Session but neuters lifecycle.

    The Flask request-teardown hook closes the sessions it finds on ``g``. In
    tests the session lifecycle is owned by the connection/session fixtures, so
    ``close`` and ``rollback`` must not propagate -- otherwise the second
    request in a multi-request test would hit a closed session, and a route
    error would roll back the test's own setup.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def close(self) -> None:  # called by close_request_sessions
        pass

    def rollback(self) -> None:  # called by close_request_sessions on error
        # Roll back only to the active savepoint so the outer test transaction
        # and prior savepoints survive. SQLAlchemy's create_savepoint mode
        # re-establishes a savepoint after a real rollback, but we want the
        # test to stay in control, so we simply swallow it here.
        pass

    def __getattr__(self, name: str) -> Any:
        return getattr(self._session, name)


class SeedData(NamedTuple):
    """Entities seeded for an authenticated e2e request."""

    user: User
    project: Project
    response_store: ResponseStore
    survey: Survey
    published_version: SurveyVersion


@pytest.fixture(autouse=True)
def _mock_session_encryption(monkeypatch: pytest.MonkeyPatch) -> None:
    """Auto-mock envelope creation so e2e tests run without AWS."""
    from app.services.public_submissions.core.session_starter import SessionStarter

    monkeypatch.setattr(
        SessionStarter,
        "_create_response_envelope",
        lambda self, db, response_db, *, session: (b"\x00" * 32, b"\x01" * 32),
    )


@pytest.fixture
def seed(core_db_session: Session) -> SeedData:
    """Seed a project member (with survey permissions) and a public, published survey.

    The user is a real ``ProjectMembership`` whose ``ProjectRole`` is granted the
    survey view/edit permissions, so the survey-permission decorator passes for
    real. The survey is public with ``published_version_id`` set so the public
    link-resolution endpoint can resolve it without auth.
    """
    user = make_user(auth0_user_id=_MEMBER_SUB, email="member@example.com")
    core_db_session.add(user)
    core_db_session.flush()

    project = make_project(user.id)
    core_db_session.add(project)
    core_db_session.flush()

    # Grant the role the permissions the survey-link routes require. The
    # permission rows are seeded into the real DB at app startup, so we look
    # them up by name rather than creating them here.
    role = make_project_role(project.id)
    role.permissions = per.get_permissions_by_names(core_db_session, _GRANTED_PERMISSIONS)
    core_db_session.add(role)
    core_db_session.flush()

    membership = ProjectMembership()
    membership.user_id = user.id
    membership.project_id = project.id
    membership.role_id = role.id
    core_db_session.add(membership)
    core_db_session.flush()

    store = make_response_store(project.id, user.id)
    core_db_session.add(store)
    core_db_session.flush()

    survey = make_survey(project.id, store.id, user.id)
    survey.visibility = "public"
    survey.public_slug = "e2e-public-survey"  # public surveys require a slug
    core_db_session.add(survey)
    core_db_session.flush()

    version = make_survey_version(survey.id, user.id, status="published")
    # A published version requires a compiled schema and a publish timestamp.
    version.compiled_schema = {"nodes": []}
    version.published_at = datetime.now(UTC)
    core_db_session.add(version)
    core_db_session.flush()

    survey.published_version_id = version.id
    core_db_session.flush()

    return SeedData(
        user=user,
        project=project,
        response_store=store,
        survey=survey,
        published_version=version,
    )


@pytest.fixture
def authed_client(
    app: Flask,
    core_db_session: Session,
    response_db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[FlaskClient]:
    """A Flask test client wired to the test's isolated sessions and seeded auth.

    Every request reuses ``core_db_session`` / ``response_db_session`` via the
    patched session factories, and authenticates as the seeded project member
    via patched token verification.
    """
    core_proxy = _NonClosingSession(core_db_session)
    response_proxy = _NonClosingSession(response_db_session)

    # open_request_sessions() calls these to populate g.core_db / g.response_db.
    monkeypatch.setattr(db_manager, "create_core_session", lambda: core_proxy)
    monkeypatch.setattr(db_manager, "create_response_session", lambda: response_proxy)

    # Bypass JWKS verification so any bearer token is accepted as the seeded member.
    # ``optional_auth`` checks the Authorization header before calling
    # ``_verify_access_token``; setting ``environ_base`` ensures the header is
    # present on every request so the route resolves an actor instead of
    # treating the request as anonymous.
    monkeypatch.setattr(auth, "_verify_access_token", lambda _token: {"sub": _MEMBER_SUB})

    with app.test_client() as client:
        client.environ_base["HTTP_AUTHORIZATION"] = "Bearer test-token"
        yield client
