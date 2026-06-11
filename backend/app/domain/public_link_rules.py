from __future__ import annotations

from datetime import UTC, datetime

from app.domain.errors import (
    LinkAlreadyUsedError,
    LinkAssignmentMismatchError,
    LinkAuthRequiredError,
    LinkExpiredError,
    LinkInactiveError,
    LinkNotFoundError,
)
from app.schema.orm.core.survey_access import SurveyLink


def ensure_is_active(*, link: SurveyLink) -> None:
    if not link.is_active:
        raise LinkInactiveError()


def ensure_not_expired(*, link: SurveyLink) -> None:
    if link.expires_at is not None and link.expires_at < datetime.now(UTC):
        raise LinkExpiredError()


def ensure_not_used(*, link: SurveyLink) -> None:
    """Single-use links (those with an assigned_email) cannot be used twice."""
    if link.is_single_use and link.used_at is not None:
        raise LinkAlreadyUsedError()


def ensure_auth_satisfied(*, link: SurveyLink, actor_email: str | None) -> None:
    """A link that requires auth must be accessed by an authenticated user."""
    if link.requires_auth and actor_email is None:
        raise LinkAuthRequiredError()


def ensure_actor_matches_assignment(*, link: SurveyLink, actor_email: str | None) -> None:
    """If the link has an assigned email and an actor is present, they must match.

    Anonymous access to an assigned link (private invite) is allowed when the link
    does not require auth — the bearer-token possession is the proof of identity.
    """
    if link.assigned_email is None or actor_email is None:
        return
    if actor_email.strip().lower() != link.assigned_email.lower():
        raise LinkAssignmentMismatchError()


def ensure_survey_id_matches(*, link: SurveyLink, survey_id: int) -> None:
    if link.survey_id != survey_id:
        raise LinkNotFoundError()
