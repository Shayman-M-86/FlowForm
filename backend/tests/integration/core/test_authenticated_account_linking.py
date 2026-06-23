"""Authenticated account-linking endpoint tests.

Covers: SurveyResolveService.verify_authenticated_link_participant
Docs: Authenticated-link-access-Flow.md §5
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.domain.errors import (
    LinkAuthRequiredError,
    ParticipantIdentityEmailMismatchError,
)
from app.repositories.core import project_subject_tokens as sub_tok
from app.schema.api.requests.survey_access_links import ResolveSurveyAccessLinkTokenRequest
from app.schema.orm.core.survey import Survey
from app.schema.orm.core.survey_access import SurveyLink
from app.schema.orm.core.user import User
from app.services.public_submissions.api.survey_resolve import SurveyResolveService
from tests.integration.core.factories import make_participant_chain, make_token, make_user


def _make_auth_link(
    db_session: Session,
    *,
    survey: Survey,
    assigned_participant_id: object,
) -> tuple[SurveyLink, str]:
    raw_token = make_token()
    link = SurveyLink(
        project_id=survey.project_id,
        survey_id=survey.id,
        name="Auth link",
        token=raw_token,
        link_type="authenticated",
        assignment_source="manual",
        assigned_participant_id=assigned_participant_id,
    )
    db_session.add(link)
    db_session.flush()
    return link, raw_token


def _resolve_payload(raw_token: str) -> ResolveSurveyAccessLinkTokenRequest:
    return ResolveSurveyAccessLinkTokenRequest.model_validate({"token": raw_token})


def test_non_authenticated_link_raises_on_account_linking_endpoint(
    db_session: Session,
    survey: Survey,
    user: User,
) -> None:
    """A general or private link token sent to the account-linking endpoint is rejected."""
    raw_token = make_token()
    link = SurveyLink(
        project_id=survey.project_id,
        survey_id=survey.id,
        name="General link",
        token=raw_token,
        link_type="general",
        assignment_source="manual",
    )
    db_session.add(link)
    db_session.flush()

    with pytest.raises(LinkAuthRequiredError):
        SurveyResolveService().verify_authenticated_link_participant(
            db_session,
            payload=_resolve_payload(raw_token),
            actor=user,
            recognition_token=None,
        )


def test_email_mismatch_raises(
    db_session: Session,
    survey: Survey,
) -> None:
    """Linking is rejected when the logged-in user's email differs from the participant identity."""
    participant = make_participant_chain(
        db_session,
        project_id=survey.project_id,
        subject_code="acct-link-subject",
        normalized_email="assigned@example.com",
    )
    _link, raw_token = _make_auth_link(db_session, survey=survey, assigned_participant_id=participant.id)

    other_user = make_user(auth0_user_id="auth0|other", email="other@example.com")
    db_session.add(other_user)
    db_session.flush()

    with pytest.raises(ParticipantIdentityEmailMismatchError):
        SurveyResolveService().verify_authenticated_link_participant(
            db_session,
            payload=_resolve_payload(raw_token),
            actor=other_user,
            recognition_token=None,
        )


def test_email_match_no_browser_token_issues_token(
    db_session: Session,
    survey: Survey,
    user: User,
) -> None:
    """Linking succeeds without a browser token. A new recognition token is issued."""
    participant = make_participant_chain(
        db_session,
        project_id=survey.project_id,
        subject_code="acct-link-subject-2",
        normalized_email=user.email,
    )
    link, raw_token = _make_auth_link(db_session, survey=survey, assigned_participant_id=participant.id)

    result = SurveyResolveService().verify_authenticated_link_participant(
        db_session,
        payload=_resolve_payload(raw_token),
        actor=user,
        recognition_token=None,
    )

    assert result.link.id == link.id
    assert result.raw_recognition_token is not None, "a new recognition token must be issued"


def test_browser_token_same_subject_no_cookie_rotation(
    db_session: Session,
    survey: Survey,
    user: User,
) -> None:
    """When the browser token already points to the assigned subject, no rotation needed."""
    participant = make_participant_chain(
        db_session,
        project_id=survey.project_id,
        subject_code="acct-link-subject-3",
        normalized_email=user.email,
    )
    link, raw_token = _make_auth_link(db_session, survey=survey, assigned_participant_id=participant.id)

    # Issue a token already pointing at the assigned subject.
    _, existing_raw = sub_tok.create_token(
        db_session,
        project_id=survey.project_id,
        project_subject_id=participant.project_subject_id,
    )

    result = SurveyResolveService().verify_authenticated_link_participant(
        db_session,
        payload=_resolve_payload(raw_token),
        actor=user,
        recognition_token=existing_raw,
    )

    assert result.link.id == link.id
    assert result.raw_recognition_token is None, "no cookie update when token already points to assigned subject"


def test_browser_token_different_subject_rotated(
    db_session: Session,
    survey: Survey,
    user: User,
) -> None:
    """When the browser token points to a different subject, it is merged and rotated."""
    from app.schema.orm.core.project_subject import ProjectSubject

    participant = make_participant_chain(
        db_session,
        project_id=survey.project_id,
        subject_code="acct-link-subject-4",
        normalized_email=user.email,
    )
    link, raw_token = _make_auth_link(db_session, survey=survey, assigned_participant_id=participant.id)

    # A separate anonymous subject that currently holds the browser recognition token.
    other_subject = ProjectSubject(project_id=survey.project_id, subject_code="anon-subject")
    db_session.add(other_subject)
    db_session.flush()
    _, other_raw = sub_tok.create_token(
        db_session,
        project_id=survey.project_id,
        project_subject_id=other_subject.id,
    )

    result = SurveyResolveService().verify_authenticated_link_participant(
        db_session,
        payload=_resolve_payload(raw_token),
        actor=user,
        recognition_token=other_raw,
    )

    assert result.link.id == link.id
    assert result.raw_recognition_token is not None, "token must be rotated when subjects differ"
    # The other subject must be merged into the assigned subject.
    db_session.refresh(other_subject)
    assert other_subject.canonical_subject_id == participant.project_subject_id, (
        "weaker token subject must point to assigned subject after merge"
    )
