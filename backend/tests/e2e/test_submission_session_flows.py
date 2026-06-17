"""E2E flow matrix tests — API in, API out.

Drives every row of the 19-row flow matrix through the real HTTP stack:
  POST /api/v1/public/submission-session/start
  POST /api/v1/public/links/verification/link  (account-linking, row 19)

All tests assert only what is visible from the HTTP response and Set-Cookie
headers — no inspection of internal service calls.

``seed`` and ``authed_client`` fixtures come from conftest.py.  The seeded
member has auth0_user_id="auth0|e2e-member" and email="member@example.com".

Flow matrix:
| #  | Entry         | Auth         | Token            | Final subject    | Link consumed |
|----|---------------|--------------|------------------|------------------|---------------|
|  1 | public slug   | no           | none             | new anon         | no            |
|  2 | public slug   | no           | valid            | token subject    | no            |
|  3 | public slug   | yes          | none             | identity subject | no            |
|  4 | public slug   | yes          | same canonical   | identity subject | no            |
|  5 | public slug   | yes          | diff canonical   | identity subject | no            |
|  6 | general link  | no           | none             | new anon         | no            |
|  7 | general link  | no           | valid            | token subject    | no            |
|  8 | general link  | yes          | none             | identity subject | no            |
|  9 | general link  | yes          | same canonical   | identity subject | no            |
| 10 | general link  | yes          | diff canonical   | identity subject | no            |
| 11 | private link  | any          | none             | assigned         | yes           |
| 12 | private link  | any          | same canonical   | assigned         | yes           |
| 13 | private link  | any          | diff canonical   | assigned         | yes           |
| 14 | auth link     | no           | any              | rejected 401     | no            |
| 15 | auth link     | yes, match   | none             | assigned         | yes           |
| 16 | auth link     | yes, match   | same canonical   | assigned         | yes           |
| 17 | auth link     | yes, match   | diff canonical   | assigned         | yes           |
| 18 | auth link     | yes, no match| any              | rejected 403     | no            |
| 19 | account-link  | yes, match   | diff canonical   | assigned         | no            |
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy.orm import Session

from app.core.extensions import auth, db_manager
from app.repositories.core import project_subject_tokens as sub_tok
from app.schema.orm.core.project_subject import ProjectSubject
from app.schema.orm.core.survey_access import SurveyLink
from tests.e2e.conftest import SeedData
from tests.integration.core.factories import make_participant_chain, make_token_pair, make_user

# The seeded member's email — must match conftest.py seed fixture.
_MEMBER_EMAIL = "member@example.com"
_MEMBER_SUB = "auth0|e2e-member"

_SESSION_START_URL = "/api/v1/public/submission-session/start"
_ACCOUNT_LINK_URL = "/api/v1/public/links/verification/link"
_RECOGNITION_COOKIE = "flowform_subject_recognition"
_SESSION_COOKIE = "flowform_submission_session"


# ---------------------------------------------------------------------------
# anon_client fixture — no bearer token; optional_auth routes see actor=None
# ---------------------------------------------------------------------------


class _NonClosingSession:
    def __init__(self, session: Session) -> None:
        self._session = session

    def close(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def __getattr__(self, name: str) -> Any:
        return getattr(self._session, name)


@pytest.fixture
def authed_client(
    app: Flask,
    core_db_session: Session,
    response_db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[FlaskClient]:
    """Authenticated client — sends Authorization header so optional_auth resolves the actor."""
    core_proxy = _NonClosingSession(core_db_session)
    response_proxy = _NonClosingSession(response_db_session)
    monkeypatch.setattr(db_manager, "create_core_session", lambda: core_proxy)
    monkeypatch.setattr(db_manager, "create_response_session", lambda: response_proxy)
    monkeypatch.setattr(auth, "_verify_access_token", lambda _token: {"sub": _MEMBER_SUB})
    with app.test_client() as client:
        client.environ_base["HTTP_AUTHORIZATION"] = "Bearer test-token"
        yield client


@pytest.fixture
def anon_client(
    app: Flask,
    core_db_session: Session,
    response_db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[FlaskClient]:
    core_proxy = _NonClosingSession(core_db_session)
    response_proxy = _NonClosingSession(response_db_session)
    monkeypatch.setattr(db_manager, "create_core_session", lambda: core_proxy)
    monkeypatch.setattr(db_manager, "create_response_session", lambda: response_proxy)
    with app.test_client() as client:
        yield client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_link(
    db: Session,
    *,
    seed: SeedData,
    link_type: str,
    assigned_participant_id: object | None = None,
    name_suffix: str = "",
) -> tuple[SurveyLink, str]:
    raw, prefix, token_hash = make_token_pair()
    link = SurveyLink(
        project_id=seed.project.id,
        survey_id=seed.survey.id,
        name=f"{link_type}-link{name_suffix}",
        token_prefix=prefix,
        token_hash=token_hash,
        link_type=link_type,
        assignment_source="manual",
        assigned_participant_id=assigned_participant_id,
    )
    db.add(link)
    db.flush()
    return link, raw


def _issue_recognition_token(db: Session, *, seed: SeedData, subject: ProjectSubject) -> str:
    _, raw = sub_tok.create_token(db, project_id=seed.project.id, project_subject_id=subject.id)
    return raw


def _anon_subject(db: Session, seed: SeedData, code: str) -> ProjectSubject:
    s = ProjectSubject(project_id=seed.project.id, subject_code=code)
    db.add(s)
    db.flush()
    return s


def _start_slug(client: FlaskClient, slug: str | None, *, recognition: str | None = None) -> Any:
    if recognition:
        client.set_cookie(_RECOGNITION_COOKIE, recognition)
    return client.post(_SESSION_START_URL, json={"access": {"type": "public_slug", "public_slug": slug}})


def _start_link(client: FlaskClient, raw_token: str, *, recognition: str | None = None) -> Any:
    if recognition:
        client.set_cookie(_RECOGNITION_COOKIE, recognition)
    return client.post(_SESSION_START_URL, json={"access": {"type": "link_token", "token": raw_token}})


def _has_cookie(resp: Any, name: str) -> bool:
    return any(name in c for c in resp.headers.getlist("Set-Cookie"))


def _extract_recognition_cookie(resp: Any) -> str:
    return next(
        c.split("=", 1)[1].split(";")[0]
        for c in resp.headers.getlist("Set-Cookie")
        if _RECOGNITION_COOKIE in c
    )


def _link_consumed(db: Session, link_id: object) -> bool:
    link = db.get(SurveyLink, link_id)
    return link is not None and link.used_at is not None


# ===========================================================================
# Row 1 — public slug | no auth | no token → new anon subject, issue
# ===========================================================================


def test_row1_public_slug_anon_no_token(
    anon_client: FlaskClient,
    core_db_session: Session,
    seed: SeedData,
) -> None:
    resp = _start_slug(anon_client, seed.survey.public_slug)

    assert resp.status_code == 201, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["status"] == "in_progress"
    assert "survey_schema" not in body
    assert _has_cookie(resp, _SESSION_COOKIE)
    assert _has_cookie(resp, _RECOGNITION_COOKIE)


# ===========================================================================
# Row 2 — public slug | no auth | valid token → token subject, mark_used
# ===========================================================================


def test_row2_public_slug_anon_valid_token(
    anon_client: FlaskClient,
    core_db_session: Session,
    seed: SeedData,
) -> None:
    subject = _anon_subject(core_db_session, seed, "row2-anon")
    rec_token = _issue_recognition_token(core_db_session, seed=seed, subject=subject)

    resp = _start_slug(anon_client, seed.survey.public_slug, recognition=rec_token)

    assert resp.status_code == 201, resp.get_data(as_text=True)
    assert resp.get_json()["status"] == "in_progress"
    assert _has_cookie(resp, _SESSION_COOKIE)
    assert _has_cookie(resp, _RECOGNITION_COOKIE)


# ===========================================================================
# Row 4 — public slug | authed | same-canonical token → identity subject, mark_used
# (Row 3 is covered by test_submission_session_start.py)
# ===========================================================================


def test_row4_public_slug_authed_same_canonical_token(
    authed_client: FlaskClient,
    core_db_session: Session,
    seed: SeedData,
) -> None:
    # First call creates the identity subject and issues the recognition token.
    first = _start_slug(authed_client, seed.survey.public_slug)
    assert first.status_code == 201
    rec_token = _extract_recognition_cookie(first)

    # Second call: same user, same-canonical token → mark_used, no new token needed
    resp = _start_slug(authed_client, seed.survey.public_slug, recognition=rec_token)

    assert resp.status_code == 201, resp.get_data(as_text=True)
    assert resp.get_json()["status"] == "in_progress"
    assert _has_cookie(resp, _SESSION_COOKIE)


# ===========================================================================
# Row 5 — public slug | authed | diff-canonical token → identity subject, merge+rotate
# ===========================================================================


def test_row5_public_slug_authed_diff_canonical_token(
    authed_client: FlaskClient,
    core_db_session: Session,
    seed: SeedData,
) -> None:
    stray = _anon_subject(core_db_session, seed, "row5-stray")
    stray_token = _issue_recognition_token(core_db_session, seed=seed, subject=stray)

    resp = _start_slug(authed_client, seed.survey.public_slug, recognition=stray_token)

    assert resp.status_code == 201, resp.get_data(as_text=True)
    assert resp.get_json()["status"] == "in_progress"
    assert _has_cookie(resp, _SESSION_COOKIE)
    assert _has_cookie(resp, _RECOGNITION_COOKIE)


# ===========================================================================
# Row 6 — general link | no auth | no token → new anon subject, issue
# ===========================================================================


def test_row6_general_link_anon_no_token(
    anon_client: FlaskClient,
    core_db_session: Session,
    seed: SeedData,
) -> None:
    seed.survey.visibility = "link_only"
    seed.survey.public_slug = None
    core_db_session.flush()

    link, raw_token = _make_link(core_db_session, seed=seed, link_type="general", name_suffix="-r6")

    resp = _start_link(anon_client, raw_token)

    assert resp.status_code == 201, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["status"] == "in_progress"
    assert "survey_schema" not in body
    assert _has_cookie(resp, _SESSION_COOKIE)
    assert _has_cookie(resp, _RECOGNITION_COOKIE)


# ===========================================================================
# Row 7 — general link | no auth | valid token → token subject, mark_used
# ===========================================================================


def test_row7_general_link_anon_valid_token(
    anon_client: FlaskClient,
    core_db_session: Session,
    seed: SeedData,
) -> None:
    seed.survey.visibility = "link_only"
    seed.survey.public_slug = None
    core_db_session.flush()

    link, raw_token = _make_link(core_db_session, seed=seed, link_type="general", name_suffix="-r7")
    subject = _anon_subject(core_db_session, seed, "row7-anon")
    rec_token = _issue_recognition_token(core_db_session, seed=seed, subject=subject)

    resp = _start_link(anon_client, raw_token, recognition=rec_token)

    assert resp.status_code == 201, resp.get_data(as_text=True)
    assert resp.get_json()["status"] == "in_progress"
    assert _has_cookie(resp, _SESSION_COOKIE)
    assert _has_cookie(resp, _RECOGNITION_COOKIE)


# ===========================================================================
# Row 8 — general link | authed | no token → identity subject, issue
# ===========================================================================


def test_row8_general_link_authed_no_token(
    authed_client: FlaskClient,
    core_db_session: Session,
    seed: SeedData,
) -> None:
    seed.survey.visibility = "link_only"
    seed.survey.public_slug = None
    core_db_session.flush()

    link, raw_token = _make_link(core_db_session, seed=seed, link_type="general", name_suffix="-r8")

    resp = _start_link(authed_client, raw_token)

    assert resp.status_code == 201, resp.get_data(as_text=True)
    assert resp.get_json()["status"] == "in_progress"
    assert _has_cookie(resp, _SESSION_COOKIE)
    assert _has_cookie(resp, _RECOGNITION_COOKIE)


# ===========================================================================
# Row 9 — general link | authed | same-canonical token → identity subject, mark_used
# ===========================================================================


def test_row9_general_link_authed_same_canonical_token(
    authed_client: FlaskClient,
    core_db_session: Session,
    seed: SeedData,
) -> None:
    seed.survey.visibility = "link_only"
    seed.survey.public_slug = None
    core_db_session.flush()

    # First link creates the identity subject.
    _, raw1 = _make_link(core_db_session, seed=seed, link_type="general", name_suffix="-r9a")
    first = _start_link(authed_client, raw1)
    assert first.status_code == 201
    rec_token = _extract_recognition_cookie(first)

    # Second link, same user, same-canonical recognition token.
    link2, raw2 = _make_link(core_db_session, seed=seed, link_type="general", name_suffix="-r9b")
    resp = _start_link(authed_client, raw2, recognition=rec_token)

    assert resp.status_code == 201, resp.get_data(as_text=True)
    assert resp.get_json()["status"] == "in_progress"
    assert _has_cookie(resp, _SESSION_COOKIE)


# ===========================================================================
# Row 10 — general link | authed | diff-canonical token → identity subject, merge+rotate
# ===========================================================================


def test_row10_general_link_authed_diff_canonical_token(
    authed_client: FlaskClient,
    core_db_session: Session,
    seed: SeedData,
) -> None:
    seed.survey.visibility = "link_only"
    seed.survey.public_slug = None
    core_db_session.flush()

    link, raw_token = _make_link(core_db_session, seed=seed, link_type="general", name_suffix="-r10")
    stray = _anon_subject(core_db_session, seed, "row10-stray")
    stray_token = _issue_recognition_token(core_db_session, seed=seed, subject=stray)

    resp = _start_link(authed_client, raw_token, recognition=stray_token)

    assert resp.status_code == 201, resp.get_data(as_text=True)
    assert resp.get_json()["status"] == "in_progress"
    assert _has_cookie(resp, _SESSION_COOKIE)
    assert _has_cookie(resp, _RECOGNITION_COOKIE)


# ===========================================================================
# Row 11 — private link | any | no token → assigned, issue, consumed
# ===========================================================================


def test_row11_private_link_no_token_consumed(
    anon_client: FlaskClient,
    core_db_session: Session,
    seed: SeedData,
) -> None:
    participant = make_participant_chain(
        core_db_session,
        project_id=seed.project.id,
        subject_code="row11-assigned",
        normalized_email="row11@example.com",
    )
    link, raw_token = _make_link(
        core_db_session, seed=seed, link_type="private",
        assigned_participant_id=participant.id, name_suffix="-r11",
    )

    resp = _start_link(anon_client, raw_token)

    assert resp.status_code == 201, resp.get_data(as_text=True)
    assert resp.get_json()["status"] == "in_progress"
    assert _has_cookie(resp, _SESSION_COOKIE)
    assert _has_cookie(resp, _RECOGNITION_COOKIE)
    assert _link_consumed(core_db_session, link.id)


# ===========================================================================
# Row 12 — private link | any | same-canonical token → assigned, keep, consumed
# ===========================================================================


def test_row12_private_link_same_canonical_token_consumed(
    anon_client: FlaskClient,
    core_db_session: Session,
    seed: SeedData,
) -> None:
    participant = make_participant_chain(
        core_db_session,
        project_id=seed.project.id,
        subject_code="row12-assigned",
        normalized_email="row12@example.com",
    )
    link, raw_token = _make_link(
        core_db_session, seed=seed, link_type="private",
        assigned_participant_id=participant.id, name_suffix="-r12",
    )
    assigned_subject = core_db_session.get(ProjectSubject, participant.project_subject_id)
    assert assigned_subject is not None
    rec_token = _issue_recognition_token(core_db_session, seed=seed, subject=assigned_subject)

    resp = _start_link(anon_client, raw_token, recognition=rec_token)

    assert resp.status_code == 201, resp.get_data(as_text=True)
    assert resp.get_json()["status"] == "in_progress"
    assert _has_cookie(resp, _SESSION_COOKIE)
    assert _link_consumed(core_db_session, link.id)


# ===========================================================================
# Row 13 — private link | any | diff-canonical token → assigned, merge+rotate, consumed
# ===========================================================================


def test_row13_private_link_diff_canonical_token_consumed(
    anon_client: FlaskClient,
    core_db_session: Session,
    seed: SeedData,
) -> None:
    participant = make_participant_chain(
        core_db_session,
        project_id=seed.project.id,
        subject_code="row13-assigned",
        normalized_email="row13@example.com",
    )
    link, raw_token = _make_link(
        core_db_session, seed=seed, link_type="private",
        assigned_participant_id=participant.id, name_suffix="-r13",
    )
    stray = _anon_subject(core_db_session, seed, "row13-stray")
    stray_token = _issue_recognition_token(core_db_session, seed=seed, subject=stray)

    resp = _start_link(anon_client, raw_token, recognition=stray_token)

    assert resp.status_code == 201, resp.get_data(as_text=True)
    assert resp.get_json()["status"] == "in_progress"
    assert _has_cookie(resp, _SESSION_COOKIE)
    assert _has_cookie(resp, _RECOGNITION_COOKIE)
    assert _link_consumed(core_db_session, link.id)


# ===========================================================================
# Row 14 — auth link | not logged in → 401 rejected, link not consumed
# ===========================================================================


def test_row14_auth_link_unauthenticated_rejected(
    anon_client: FlaskClient,
    core_db_session: Session,
    seed: SeedData,
) -> None:
    participant = make_participant_chain(
        core_db_session,
        project_id=seed.project.id,
        subject_code="row14-assigned",
        normalized_email=_MEMBER_EMAIL,
        user_id=seed.user.id,
    )
    link, raw_token = _make_link(
        core_db_session, seed=seed, link_type="authenticated",
        assigned_participant_id=participant.id, name_suffix="-r14",
    )

    resp = _start_link(anon_client, raw_token)

    assert resp.status_code == 401, resp.get_data(as_text=True)
    assert not _link_consumed(core_db_session, link.id)


# ===========================================================================
# Row 15 — auth link | authed, matching identity | no token → assigned, issue, consumed
# ===========================================================================


def test_row15_auth_link_matching_no_token_consumed(
    authed_client: FlaskClient,
    core_db_session: Session,
    seed: SeedData,
) -> None:
    participant = make_participant_chain(
        core_db_session,
        project_id=seed.project.id,
        subject_code="row15-assigned",
        normalized_email=_MEMBER_EMAIL,
        user_id=seed.user.id,
    )
    link, raw_token = _make_link(
        core_db_session, seed=seed, link_type="authenticated",
        assigned_participant_id=participant.id, name_suffix="-r15",
    )

    resp = _start_link(authed_client, raw_token)

    assert resp.status_code == 201, resp.get_data(as_text=True)
    assert resp.get_json()["status"] == "in_progress"
    assert _has_cookie(resp, _SESSION_COOKIE)
    assert _has_cookie(resp, _RECOGNITION_COOKIE)
    assert _link_consumed(core_db_session, link.id)


# ===========================================================================
# Row 16 — auth link | authed, match | same-canonical token → assigned, keep, consumed
# ===========================================================================


def test_row16_auth_link_matching_same_canonical_token_consumed(
    authed_client: FlaskClient,
    core_db_session: Session,
    seed: SeedData,
) -> None:
    participant = make_participant_chain(
        core_db_session,
        project_id=seed.project.id,
        subject_code="row16-assigned",
        normalized_email=_MEMBER_EMAIL,
        user_id=seed.user.id,
    )
    link, raw_token = _make_link(
        core_db_session, seed=seed, link_type="authenticated",
        assigned_participant_id=participant.id, name_suffix="-r16",
    )
    assigned_subject = core_db_session.get(ProjectSubject, participant.project_subject_id)
    assert assigned_subject is not None
    rec_token = _issue_recognition_token(core_db_session, seed=seed, subject=assigned_subject)

    resp = _start_link(authed_client, raw_token, recognition=rec_token)

    assert resp.status_code == 201, resp.get_data(as_text=True)
    assert resp.get_json()["status"] == "in_progress"
    assert _has_cookie(resp, _SESSION_COOKIE)
    assert _link_consumed(core_db_session, link.id)


# ===========================================================================
# Row 17 — auth link | authed, match | diff-canonical token → assigned, merge+rotate, consumed
# ===========================================================================


def test_row17_auth_link_matching_diff_canonical_token_consumed(
    authed_client: FlaskClient,
    core_db_session: Session,
    seed: SeedData,
) -> None:
    participant = make_participant_chain(
        core_db_session,
        project_id=seed.project.id,
        subject_code="row17-assigned",
        normalized_email=_MEMBER_EMAIL,
        user_id=seed.user.id,
    )
    link, raw_token = _make_link(
        core_db_session, seed=seed, link_type="authenticated",
        assigned_participant_id=participant.id, name_suffix="-r17",
    )
    stray = _anon_subject(core_db_session, seed, "row17-stray")
    stray_token = _issue_recognition_token(core_db_session, seed=seed, subject=stray)

    resp = _start_link(authed_client, raw_token, recognition=stray_token)

    assert resp.status_code == 201, resp.get_data(as_text=True)
    assert resp.get_json()["status"] == "in_progress"
    assert _has_cookie(resp, _SESSION_COOKIE)
    assert _has_cookie(resp, _RECOGNITION_COOKIE)
    assert _link_consumed(core_db_session, link.id)


# ===========================================================================
# Row 18 — auth link | authed, wrong identity → 403 rejected, not consumed
# ===========================================================================


def test_row18_auth_link_identity_mismatch_rejected(
    authed_client: FlaskClient,
    core_db_session: Session,
    seed: SeedData,
) -> None:
    other_user = make_user(auth0_user_id="auth0|row18-other", email="other-row18@example.com")
    core_db_session.add(other_user)
    core_db_session.flush()

    participant = make_participant_chain(
        core_db_session,
        project_id=seed.project.id,
        subject_code="row18-assigned",
        normalized_email="other-row18@example.com",
        user_id=other_user.id,
    )
    link, raw_token = _make_link(
        core_db_session, seed=seed, link_type="authenticated",
        assigned_participant_id=participant.id, name_suffix="-r18",
    )

    # authed_client authenticates as _MEMBER_EMAIL, not other_user
    resp = _start_link(authed_client, raw_token)

    assert resp.status_code == 403, resp.get_data(as_text=True)
    assert not _link_consumed(core_db_session, link.id)


# ===========================================================================
# Row 19 — account-linking | authed, email match | diff-canonical → rotate, no consume
# ===========================================================================


def test_row19_account_linking_email_match_merge_rotate(
    authed_client: FlaskClient,
    core_db_session: Session,
    seed: SeedData,
) -> None:
    # Email-only identity (no user_id yet) matching the seeded member's email.
    participant = make_participant_chain(
        core_db_session,
        project_id=seed.project.id,
        subject_code="row19-assigned",
        normalized_email=_MEMBER_EMAIL,
        user_id=None,
    )
    link, raw_token = _make_link(
        core_db_session, seed=seed, link_type="authenticated",
        assigned_participant_id=participant.id, name_suffix="-r19",
    )

    stray = _anon_subject(core_db_session, seed, "row19-stray")
    stray_token = _issue_recognition_token(core_db_session, seed=seed, subject=stray)

    authed_client.set_cookie(_RECOGNITION_COOKIE, stray_token)
    resp = authed_client.post(_ACCOUNT_LINK_URL, json={"token": raw_token})

    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert _has_cookie(resp, _RECOGNITION_COOKIE)
    assert not _link_consumed(core_db_session, link.id), "account-linking must not consume the link"
