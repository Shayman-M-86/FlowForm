"""End-to-end flow matrix tests.

One test per row of docs/Policies-and-Services/implementation/flow-matrix.md.
All tests run through SessionStarter.start() so they exercise the full
orchestration path: access resolution → subject resolution → token action →
session creation → link consumption.

Rejection tests assert the domain error raised by AccessResolver before
subject resolution begins.

Stop condition: if any test would need behavior not yet implemented, skip it
with a comment rather than implement service-level changes here.

Docs:
  implementation/flow-matrix.md
  Flows/Public-slug-flow.md
  Flows/General-Link-Flow.md
  Flows/Private-link-access-Flow.md
  Flows/Authenticated-link-access-Flow.md
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import LinkAssignmentMismatchError, LinkAuthRequiredError
from app.repositories.core import project_subject_identities as sub_id
from app.repositories.core import project_subject_tokens as sub_tok
from app.schema.api.requests.submission_sessions import StartSubmissionSessionRequest
from app.schema.enums import SurveyVisibility
from app.schema.orm.core.project_subject import ProjectSubject
from app.schema.orm.core.submission_session import SubmissionSession
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.survey_access import SurveyLink
from app.schema.orm.core.user import User
from app.services.public_submissions.core.session_starter import SessionStarter
from tests.integration.core.factories import make_participant_chain, make_token_pair, make_user

# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------

_SCHEMA = {"nodes": []}


def _publish(
    db: Session,
    *,
    survey: Survey,
    survey_version: SurveyVersion,
    visibility: SurveyVisibility = "public",
    slug: str | None = "fm-test-survey",
) -> None:
    survey.visibility = visibility
    survey.public_slug = slug if visibility == "public" else None
    survey_version.status = "published"
    survey_version.compiled_schema = _SCHEMA
    survey_version.published_at = datetime.now(UTC)
    db.flush()
    survey.published_version_id = survey_version.id
    db.flush()


def _make_link(
    db: Session,
    *,
    survey: Survey,
    link_type: str = "general",
    assigned_participant_id: object | None = None,
    slug_suffix: str = "",
) -> tuple[SurveyLink, str]:
    raw_token, token_prefix, token_hash = make_token_pair()
    link = SurveyLink(
        project_id=survey.project_id,
        survey_id=survey.id,
        name=f"{link_type}-link{slug_suffix}",
        token_prefix=token_prefix,
        token_hash=token_hash,
        link_type=link_type,
        assignment_source="manual",
        assigned_participant_id=assigned_participant_id,
    )
    db.add(link)
    db.flush()
    return link, raw_token


def _make_subject(db: Session, *, project_id: int, code: str) -> ProjectSubject:
    s = ProjectSubject(project_id=project_id, subject_code=code)
    db.add(s)
    db.flush()
    return s


def _issue_token_for(db: Session, *, project_id: int, subject: ProjectSubject) -> str:
    _, raw = sub_tok.create_token(db, project_id=project_id, project_subject_id=subject.id)
    return raw


def _slug_payload(slug: str) -> StartSubmissionSessionRequest:
    return StartSubmissionSessionRequest.model_validate(
        {"access": {"type": "public_slug", "public_slug": slug}}
    )


def _token_payload(raw_token: str) -> StartSubmissionSessionRequest:
    return StartSubmissionSessionRequest.model_validate(
        {"access": {"type": "link_token", "token": raw_token}}
    )


def _session_for_survey(db: Session, survey_id: int) -> SubmissionSession | None:
    return db.scalar(select(SubmissionSession).where(SubmissionSession.survey_id == survey_id))


def _session_for_link(db: Session, link_id: object) -> SubmissionSession | None:
    return db.scalar(select(SubmissionSession).where(SubmissionSession.link_id == link_id))


# ---------------------------------------------------------------------------
# Row 1: public slug | no actor | no token → new anonymous subject, issue token
# ---------------------------------------------------------------------------


def test_public_slug_no_actor_no_token_creates_anonymous_subject_issues_token(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    """Row 1: public slug, unauthenticated, no recognition token.

    Final subject: new anonymous subject.
    Token action: issue.
    Link consumed: no.
    """
    _publish(db_session, survey=survey, survey_version=survey_version, slug="fm-row1")

    _response, browser_token, recognition_token = SessionStarter().start(
        db_session, db_session,
        payload=_slug_payload("fm-row1"),
        actor=None,
        recognition_token=None,
    )

    session = _session_for_survey(db_session, survey.id)
    assert session is not None, "session must be created"
    assert session.project_subject_id is not None, "anonymous subject must be created and assigned"
    assert browser_token, "browser session token must be issued"
    assert recognition_token is not None, "recognition token must be issued for new anonymous subject"


# ---------------------------------------------------------------------------
# Row 2: public slug | no actor | valid canonical token → token subject, mark used
# ---------------------------------------------------------------------------


def test_public_slug_no_actor_valid_canonical_token_uses_token_subject(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    """Row 2: public slug, unauthenticated, recognition token present (token = canonical subject).

    Final subject: token subject.
    Token action: mark used (recognition_token returned unchanged).
    Link consumed: no.
    """
    _publish(db_session, survey=survey, survey_version=survey_version, slug="fm-row2")
    existing_subject = _make_subject(db_session, project_id=survey.project_id, code="fm-row2-subj")
    existing_raw = _issue_token_for(db_session, project_id=survey.project_id, subject=existing_subject)

    _response, browser_token, recognition_token = SessionStarter().start(
        db_session, db_session,
        payload=_slug_payload("fm-row2"),
        actor=None,
        recognition_token=existing_raw,
    )

    session = _session_for_survey(db_session, survey.id)
    assert session is not None
    assert session.project_subject_id == existing_subject.id, "must reuse token subject"
    assert browser_token, "browser token must be issued"
    # mark_used → existing raw returned; apply_token_action returns existing_raw for mark_used
    assert recognition_token == existing_raw, "recognition token unchanged on mark_used"


# ---------------------------------------------------------------------------
# Row 3: public slug | logged-in | no token → logged-in identity subject, issue
# ---------------------------------------------------------------------------


def test_public_slug_logged_in_no_token_creates_or_uses_identity_subject(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
    user: User,
) -> None:
    """Row 3: public slug, authenticated actor, no recognition token.

    Final subject: logged-in identity subject (created + identity written).
    Token action: issue.
    Link consumed: no.
    """
    _publish(db_session, survey=survey, survey_version=survey_version, slug="fm-row3")

    _response, browser_token, recognition_token = SessionStarter().start(
        db_session, db_session,
        payload=_slug_payload("fm-row3"),
        actor=user,
        recognition_token=None,
    )

    session = _session_for_survey(db_session, survey.id)
    assert session is not None
    assert session.project_subject_id is not None, "subject must be created for logged-in user"
    assert browser_token
    assert recognition_token is not None, "token must be issued for new identity subject"

    # Verify identity row written for the actor.
    identity = sub_id.get_active_user_identity(db_session, project_id=survey.project_id, user_id=user.id)
    assert identity is not None, "user identity must be written"
    assert identity.project_subject_id == session.project_subject_id


# ---------------------------------------------------------------------------
# Row 4: public slug | logged-in | valid token, different canonical → merge, rotate
# ---------------------------------------------------------------------------


def test_public_slug_logged_in_different_canonical_token_merges_and_rotates(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
    user: User,
) -> None:
    """Row 4: public slug, authenticated actor, recognition token points to different subject.

    Final subject: logged-in identity subject.
    Token action: rotate (new token issued, old revoked).
    Weaker (token) subject merged into identity subject.
    Link consumed: no.
    """
    _publish(db_session, survey=survey, survey_version=survey_version, slug="fm-row4")

    # Pre-create identity subject for the user.
    identity_subject = _make_subject(db_session, project_id=survey.project_id, code="fm-row4-identity")
    sub_id.create_user_identity(
        db_session,
        project_id=survey.project_id,
        project_subject_id=identity_subject.id,
        user=user,
    )

    # A separate anonymous subject that holds the recognition token.
    token_subject = _make_subject(db_session, project_id=survey.project_id, code="fm-row4-token")
    old_raw = _issue_token_for(db_session, project_id=survey.project_id, subject=token_subject)

    _response, browser_token, recognition_token = SessionStarter().start(
        db_session, db_session,
        payload=_slug_payload("fm-row4"),
        actor=user,
        recognition_token=old_raw,
    )

    session = _session_for_survey(db_session, survey.id)
    assert session is not None
    assert session.project_subject_id == identity_subject.id, "identity subject must win"

    # rotate: new token issued for final (identity) subject.
    assert recognition_token is not None, "new recognition token must be issued after rotation"
    assert recognition_token != old_raw, "rotated token must differ from old"

    # Token subject merged into identity subject.
    db_session.refresh(token_subject)
    assert token_subject.canonical_subject_id == identity_subject.id, (
        "weaker token subject must point to identity subject"
    )


# ---------------------------------------------------------------------------
# Row 5: general link | no actor | valid canonical token → token subject, mark used
# ---------------------------------------------------------------------------


def test_general_link_no_actor_valid_token_uses_token_subject(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    """Row 5: general link, unauthenticated, recognition token present.

    Final subject: token subject.
    Token action: mark used.
    Link consumed: no (general link is reusable).
    """
    _publish(db_session, survey=survey, survey_version=survey_version, visibility="link_only", slug=None)
    _link, raw_link_token = _make_link(db_session, survey=survey, link_type="general", slug_suffix="-row5")

    existing_subject = _make_subject(db_session, project_id=survey.project_id, code="fm-row5-subj")
    existing_raw = _issue_token_for(db_session, project_id=survey.project_id, subject=existing_subject)

    _response, browser_token, recognition_token = SessionStarter().start(
        db_session, db_session,
        payload=_token_payload(raw_link_token),
        actor=None,
        recognition_token=existing_raw,
    )

    session = _session_for_link(db_session, _link.id)
    assert session is not None
    assert session.project_subject_id == existing_subject.id, "must reuse token subject"
    assert _link.used_at is None, "general link must not be consumed"
    assert recognition_token == existing_raw, "mark_used returns existing raw"


# ---------------------------------------------------------------------------
# Row 6: general link | logged-in | valid token, different canonical → merge, rotate
# ---------------------------------------------------------------------------


def test_general_link_logged_in_different_canonical_token_merges_and_rotates(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
    user: User,
) -> None:
    """Row 6: general link, authenticated actor, recognition token points to different subject.

    Final subject: logged-in identity subject.
    Token action: rotate.
    Link consumed: no.
    """
    _publish(db_session, survey=survey, survey_version=survey_version, visibility="link_only", slug=None)
    _link, raw_link_token = _make_link(db_session, survey=survey, link_type="general", slug_suffix="-row6")

    identity_subject = _make_subject(db_session, project_id=survey.project_id, code="fm-row6-identity")
    sub_id.create_user_identity(
        db_session,
        project_id=survey.project_id,
        project_subject_id=identity_subject.id,
        user=user,
    )
    token_subject = _make_subject(db_session, project_id=survey.project_id, code="fm-row6-token")
    old_raw = _issue_token_for(db_session, project_id=survey.project_id, subject=token_subject)

    _response, browser_token, recognition_token = SessionStarter().start(
        db_session, db_session,
        payload=_token_payload(raw_link_token),
        actor=user,
        recognition_token=old_raw,
    )

    session = _session_for_link(db_session, _link.id)
    assert session is not None
    assert session.project_subject_id == identity_subject.id, "identity subject must win"
    assert _link.used_at is None, "general link must not be consumed"
    assert recognition_token is not None and recognition_token != old_raw, "token must be rotated"

    db_session.refresh(token_subject)
    assert token_subject.canonical_subject_id == identity_subject.id


# ---------------------------------------------------------------------------
# Row 7: private link | no token → assigned subject, issue token, link consumed
# ---------------------------------------------------------------------------


def test_private_link_no_token_uses_assigned_subject_and_consumes_link(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    """Row 7a: private link, any auth, no recognition token.

    Final subject: assigned subject.
    Token action: issue.
    Link consumed: yes on session start.
    """
    _publish(db_session, survey=survey, survey_version=survey_version, slug="fm-row7a")
    participant = make_participant_chain(
        db_session, project_id=survey.project_id, subject_code="fm-row7a-assigned"
    )
    link, raw_link_token = _make_link(
        db_session,
        survey=survey,
        link_type="private",
        assigned_participant_id=participant.id,
        slug_suffix="-row7a",
    )

    _response, browser_token, recognition_token = SessionStarter().start(
        db_session, db_session,
        payload=_token_payload(raw_link_token),
        actor=None,
        recognition_token=None,
    )

    session = _session_for_link(db_session, link.id)
    assert session is not None
    assert session.project_subject_id == participant.project_subject_id, "assigned subject must be used"
    assert link.used_at is not None, "private link must be consumed on session start"
    assert recognition_token is not None, "recognition token must be issued for assigned subject"


# ---------------------------------------------------------------------------
# Row 8: private link | valid token, different canonical → merge, rotate, consumed
# ---------------------------------------------------------------------------


def test_private_link_different_canonical_token_merges_rotates_and_consumes(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    """Row 7b (matrix row 8): private link, recognition token points to different subject.

    Final subject: assigned subject.
    Token action: rotate.
    Link consumed: yes.
    """
    _publish(db_session, survey=survey, survey_version=survey_version, slug="fm-row8")
    participant = make_participant_chain(
        db_session, project_id=survey.project_id, subject_code="fm-row8-assigned"
    )
    link, raw_link_token = _make_link(
        db_session,
        survey=survey,
        link_type="private",
        assigned_participant_id=participant.id,
        slug_suffix="-row8",
    )

    stray_subject = _make_subject(db_session, project_id=survey.project_id, code="fm-row8-stray")
    old_raw = _issue_token_for(db_session, project_id=survey.project_id, subject=stray_subject)

    _response, browser_token, recognition_token = SessionStarter().start(
        db_session, db_session,
        payload=_token_payload(raw_link_token),
        actor=None,
        recognition_token=old_raw,
    )

    session = _session_for_link(db_session, link.id)
    assert session is not None
    assert session.project_subject_id == participant.project_subject_id, "assigned subject must win"
    assert link.used_at is not None, "private link must be consumed"
    assert recognition_token is not None and recognition_token != old_raw, "token must be rotated"

    db_session.refresh(stray_subject)
    assert stray_subject.canonical_subject_id == participant.project_subject_id, (
        "stray subject must be merged into assigned subject"
    )


# ---------------------------------------------------------------------------
# Row 9 (rejection): authenticated link | not logged in → LinkAuthRequiredError
# ---------------------------------------------------------------------------


def test_authenticated_link_unauthenticated_actor_rejected(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
    user: User,
) -> None:
    """Row 9 (rejection): authenticated link accessed without logging in.

    Access rejected before subject resolution.
    """
    _publish(db_session, survey=survey, survey_version=survey_version, slug="fm-row9")
    participant = make_participant_chain(
        db_session,
        project_id=survey.project_id,
        subject_code="fm-row9-assigned",
        normalized_email=user.email,
        user_id=user.id,
    )
    link, raw_link_token = _make_link(
        db_session,
        survey=survey,
        link_type="authenticated",
        assigned_participant_id=participant.id,
        slug_suffix="-row9",
    )

    with pytest.raises(LinkAuthRequiredError):
        SessionStarter().start(
            db_session, db_session,
            payload=_token_payload(raw_link_token),
            actor=None,  # not logged in
            recognition_token=None,
        )

    assert _session_for_link(db_session, link.id) is None, "no session must be created on rejection"


# ---------------------------------------------------------------------------
# Row 10: authenticated link | matching identity, no token → assigned subject, issue
# ---------------------------------------------------------------------------


def test_authenticated_link_matching_identity_no_token_creates_session(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
    user: User,
) -> None:
    """Row 10: authenticated link, logged-in user matches assigned identity, no recognition token.

    Final subject: assigned subject.
    Token action: issue.
    Link consumed: yes on session start.
    """
    _publish(db_session, survey=survey, survey_version=survey_version, slug="fm-row10")
    participant = make_participant_chain(
        db_session,
        project_id=survey.project_id,
        subject_code="fm-row10-assigned",
        normalized_email=user.email,
        user_id=user.id,
    )
    link, raw_link_token = _make_link(
        db_session,
        survey=survey,
        link_type="authenticated",
        assigned_participant_id=participant.id,
        slug_suffix="-row10",
    )

    _response, browser_token, recognition_token = SessionStarter().start(
        db_session, db_session,
        payload=_token_payload(raw_link_token),
        actor=user,
        recognition_token=None,
    )

    session = _session_for_link(db_session, link.id)
    assert session is not None
    assert session.project_subject_id == participant.project_subject_id, "assigned subject must be used"
    assert link.used_at is not None, "authenticated link must be consumed on session start"
    assert recognition_token is not None, "recognition token must be issued"


# ---------------------------------------------------------------------------
# Row 11: authenticated link | matching identity, different canonical token → merge, rotate
# ---------------------------------------------------------------------------


def test_authenticated_link_matching_identity_different_token_merges_and_rotates(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
    user: User,
) -> None:
    """Row 11: authenticated link, matching identity, recognition token points to different subject.

    Final subject: assigned subject.
    Token action: rotate.
    Link consumed: yes.
    """
    _publish(db_session, survey=survey, survey_version=survey_version, slug="fm-row11")
    participant = make_participant_chain(
        db_session,
        project_id=survey.project_id,
        subject_code="fm-row11-assigned",
        normalized_email=user.email,
        user_id=user.id,
    )
    link, raw_link_token = _make_link(
        db_session,
        survey=survey,
        link_type="authenticated",
        assigned_participant_id=participant.id,
        slug_suffix="-row11",
    )

    stray_subject = _make_subject(db_session, project_id=survey.project_id, code="fm-row11-stray")
    old_raw = _issue_token_for(db_session, project_id=survey.project_id, subject=stray_subject)

    _response, browser_token, recognition_token = SessionStarter().start(
        db_session, db_session,
        payload=_token_payload(raw_link_token),
        actor=user,
        recognition_token=old_raw,
    )

    session = _session_for_link(db_session, link.id)
    assert session is not None
    assert session.project_subject_id == participant.project_subject_id
    assert link.used_at is not None
    assert recognition_token is not None and recognition_token != old_raw

    db_session.refresh(stray_subject)
    assert stray_subject.canonical_subject_id == participant.project_subject_id


# ---------------------------------------------------------------------------
# Row 12 (rejection): authenticated link | non-matching identity → rejected
# ---------------------------------------------------------------------------


def test_authenticated_link_non_matching_identity_rejected(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
    user: User,
) -> None:
    """Row 12 (rejection): authenticated link, logged-in user does not match assigned identity.

    Access rejected before subject resolution.
    """
    _publish(db_session, survey=survey, survey_version=survey_version, slug="fm-row12")

    # Assign to user, but attempt access as different_user.
    participant = make_participant_chain(
        db_session,
        project_id=survey.project_id,
        subject_code="fm-row12-assigned",
        normalized_email=user.email,
        user_id=user.id,
    )
    link, raw_link_token = _make_link(
        db_session,
        survey=survey,
        link_type="authenticated",
        assigned_participant_id=participant.id,
        slug_suffix="-row12",
    )

    different_user = make_user(auth0_user_id="auth0|other-row12", email="other-row12@example.com")
    db_session.add(different_user)
    db_session.flush()

    with pytest.raises(LinkAssignmentMismatchError):
        SessionStarter().start(
            db_session, db_session,
            payload=_token_payload(raw_link_token),
            actor=different_user,
            recognition_token=None,
        )

    assert _session_for_link(db_session, link.id) is None, "no session must be created on rejection"


# ---------------------------------------------------------------------------
# New rows: general link | no token (anonymous + logged-in)
# ---------------------------------------------------------------------------


def test_general_link_no_actor_no_token_creates_anonymous_subject_issues_token(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    """General link, unauthenticated, no recognition token.

    Final subject: new anonymous subject.
    Token action: issue.
    Link consumed: no.
    """
    _publish(db_session, survey=survey, survey_version=survey_version, visibility="link_only", slug=None)
    link, raw_link_token = _make_link(db_session, survey=survey, link_type="general", slug_suffix="-gl-anon-notoken")

    _response, browser_token, recognition_token = SessionStarter().start(
        db_session, db_session,
        payload=_token_payload(raw_link_token),
        actor=None,
        recognition_token=None,
    )

    session = _session_for_link(db_session, link.id)
    assert session is not None
    assert session.project_subject_id is not None, "new anonymous subject must be created"
    assert link.used_at is None, "general link must not be consumed"
    assert recognition_token is not None, "recognition token must be issued for new anonymous subject"


def test_general_link_logged_in_no_token_creates_identity_subject(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
    user: User,
) -> None:
    """General link, authenticated actor, no recognition token.

    Final subject: logged-in identity subject (created + identity written).
    Token action: issue.
    Link consumed: no.
    """
    _publish(db_session, survey=survey, survey_version=survey_version, visibility="link_only", slug=None)
    link, raw_link_token = _make_link(db_session, survey=survey, link_type="general", slug_suffix="-gl-auth-notoken")

    _response, browser_token, recognition_token = SessionStarter().start(
        db_session, db_session,
        payload=_token_payload(raw_link_token),
        actor=user,
        recognition_token=None,
    )

    session = _session_for_link(db_session, link.id)
    assert session is not None
    assert session.project_subject_id is not None
    assert link.used_at is None, "general link must not be consumed"
    assert recognition_token is not None, "token must be issued for new identity subject"

    identity = sub_id.get_active_user_identity(db_session, project_id=survey.project_id, user_id=user.id)
    assert identity is not None, "user identity must be written"
    assert identity.project_subject_id == session.project_subject_id


# ---------------------------------------------------------------------------
# Same-canonical rows: token already points to canonical subject — mark_used / keep
# ---------------------------------------------------------------------------


def test_public_slug_logged_in_same_canonical_token_mark_used(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
    user: User,
) -> None:
    """Public slug, authenticated actor, token already points to identity subject (same canonical).

    Final subject: logged-in identity subject.
    Token action: mark_used — existing raw token returned unchanged.
    """
    _publish(db_session, survey=survey, survey_version=survey_version, slug="fm-sc-slug")
    identity_subject = _make_subject(db_session, project_id=survey.project_id, code="fm-sc-slug-identity")
    sub_id.create_user_identity(
        db_session, project_id=survey.project_id, project_subject_id=identity_subject.id, user=user
    )
    existing_raw = _issue_token_for(db_session, project_id=survey.project_id, subject=identity_subject)

    _response, browser_token, recognition_token = SessionStarter().start(
        db_session, db_session,
        payload=_slug_payload("fm-sc-slug"),
        actor=user,
        recognition_token=existing_raw,
    )

    session = _session_for_survey(db_session, survey.id)
    assert session is not None
    assert session.project_subject_id == identity_subject.id
    assert recognition_token == existing_raw, "same-canonical: existing token returned unchanged"


def test_general_link_logged_in_same_canonical_token_mark_used(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
    user: User,
) -> None:
    """General link, authenticated actor, token already points to identity subject (same canonical).

    Final subject: logged-in identity subject.
    Token action: mark_used.
    """
    _publish(db_session, survey=survey, survey_version=survey_version, visibility="link_only", slug=None)
    link, raw_link_token = _make_link(db_session, survey=survey, link_type="general", slug_suffix="-gl-sc")
    identity_subject = _make_subject(db_session, project_id=survey.project_id, code="fm-gl-sc-identity")
    sub_id.create_user_identity(
        db_session, project_id=survey.project_id, project_subject_id=identity_subject.id, user=user
    )
    existing_raw = _issue_token_for(db_session, project_id=survey.project_id, subject=identity_subject)

    _response, browser_token, recognition_token = SessionStarter().start(
        db_session, db_session,
        payload=_token_payload(raw_link_token),
        actor=user,
        recognition_token=existing_raw,
    )

    session = _session_for_link(db_session, link.id)
    assert session is not None
    assert session.project_subject_id == identity_subject.id
    assert link.used_at is None
    assert recognition_token == existing_raw, "same-canonical: existing token returned unchanged"


def test_private_link_same_canonical_token_keep(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    """Private link, token already points to assigned subject (same canonical).

    Final subject: assigned subject.
    Token action: keep — apply_token_action returns None, browser cookie unchanged.
    Link consumed: yes.
    """
    _publish(db_session, survey=survey, survey_version=survey_version, slug="fm-pl-sc")
    participant = make_participant_chain(
        db_session, project_id=survey.project_id, subject_code="fm-pl-sc-assigned"
    )
    link, raw_link_token = _make_link(
        db_session,
        survey=survey,
        link_type="private",
        assigned_participant_id=participant.id,
        slug_suffix="-pl-sc",
    )
    assigned_subject = db_session.get(ProjectSubject, participant.project_subject_id)
    assert assigned_subject is not None
    existing_raw = _issue_token_for(db_session, project_id=survey.project_id, subject=assigned_subject)

    _response, _browser_token, recognition_token = SessionStarter().start(
        db_session, db_session,
        payload=_token_payload(raw_link_token),
        actor=None,
        recognition_token=existing_raw,
    )

    session = _session_for_link(db_session, link.id)
    assert session is not None
    assert session.project_subject_id == participant.project_subject_id
    assert link.used_at is not None, "private link must be consumed"
    assert recognition_token is None, "same-canonical keep: no token update returned"


def test_authenticated_link_same_canonical_token_keep(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
    user: User,
) -> None:
    """Authenticated link, matching identity, token already points to assigned subject (same canonical).

    Final subject: assigned subject.
    Token action: keep.
    Link consumed: yes.
    """
    _publish(db_session, survey=survey, survey_version=survey_version, slug="fm-al-sc")
    participant = make_participant_chain(
        db_session,
        project_id=survey.project_id,
        subject_code="fm-al-sc-assigned",
        normalized_email=user.email,
        user_id=user.id,
    )
    link, raw_link_token = _make_link(
        db_session,
        survey=survey,
        link_type="authenticated",
        assigned_participant_id=participant.id,
        slug_suffix="-al-sc",
    )
    assigned_subject = db_session.get(ProjectSubject, participant.project_subject_id)
    assert assigned_subject is not None
    existing_raw = _issue_token_for(db_session, project_id=survey.project_id, subject=assigned_subject)

    _response, _browser_token, recognition_token = SessionStarter().start(
        db_session, db_session,
        payload=_token_payload(raw_link_token),
        actor=user,
        recognition_token=existing_raw,
    )

    session = _session_for_link(db_session, link.id)
    assert session is not None
    assert session.project_subject_id == participant.project_subject_id
    assert link.used_at is not None
    assert recognition_token is None, "same-canonical keep: no token update returned"
